import json
import os
import re
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


load_dotenv()


Intent = Literal[
    "billing",
    "technical_issue",
    "account_access",
    "shipping",
    "general",
]

Priority = Literal["low", "medium", "high", "urgent"]


class Classification(BaseModel):
    intent: Intent = Field(description="Main customer intent")
    priority: Priority = Field(description="Support priority level")
    summary: str = Field(description="Short summary of the customer issue")
    reasoning: str = Field(description="Brief reason for the classification")


class SupportState(TypedDict, total=False):
    query: str
    top_k: int
    classification: Classification
    retrieved_passages: list[dict]
    draft_response: str
    final_response: str
    trace: list[dict]


SAMPLE_QUERIES = [
    "I was charged twice this month for the same subscription. Can you fix this?",
    "I cannot log in even after trying my password several times. Is my account blocked?",
    "Your mobile app keeps crashing whenever I open the reports page.",
    "My order tracking has not updated in four days. Where is my package?",
    "The API is returning 500 errors for our checkout requests. This is affecting customers.",
]


def add_trace(state: SupportState, step: str, data: dict) -> list[dict]:
    return state.get("trace", []) + [{"step": step, "data": data}]


def load_kb_documents(kb_path: str | Path) -> list[Document]:
    kb_text = Path(kb_path).read_text(encoding="utf-8")
    sections = re.split(r"(?=^### )", kb_text, flags=re.MULTILINE)
    documents = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.splitlines()
        header = lines[0].removeprefix("### ").strip()
        content = "\n".join(lines[1:]).strip()
        header_parts = [part.strip() for part in header.split("|")]

        article_id = header_parts[0] if len(header_parts) > 0 else "UNKNOWN"
        title = header_parts[1] if len(header_parts) > 1 else "Untitled Article"
        intent = header_parts[2] if len(header_parts) > 2 else "general"

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "article_id": article_id,
                    "title": title,
                    "intent": intent,
                },
            )
        )

    if not documents:
        raise ValueError(f"No KB articles found in {kb_path}")

    return documents


def build_vector_store(kb_path: str | Path = r"/home/ubuntu/My_learning/support_kb.txt") -> InMemoryVectorStore:
    documents = load_kb_documents(kb_path)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents)
    return vector_store


def build_graph(llm: ChatAnthropic, vector_store: InMemoryVectorStore):
    classifier_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a customer support classifier. "
                    "Classify the customer message into one intent and one priority. "
                    "Intent must be one of: billing, technical_issue, account_access, "
                    "shipping, general. Priority must be one of: low, medium, high, urgent. "
                    "Use urgent only for outages, security risks, or many customers being impacted."
                ),
            ),
            ("human", "Customer message: {query}"),
        ]
    )

    composer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a professional customer support agent. "
                    "Use the provided KB passages to draft a helpful customer response. "
                    "Be concise, empathetic, and specific. Do not invent policies."
                ),
            ),
            (
                "human",
                (
                    "Customer query:\n{query}\n\n"
                    "Classification:\n{classification}\n\n"
                    "Relevant KB passages:\n{kb_context}\n\n"
                    "Draft the customer response."
                ),
            ),
        ]
    )

    finalizer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Polish this support draft into a final customer-facing response. "
                    "Remove internal labels, KB article IDs, priority labels, and reasoning. "
                    "Keep the response professional, concise, and actionable."
                ),
            ),
            ("human", "{draft_response}"),
        ]
    )

    def classifier_agent(state: SupportState) -> SupportState:
        structured_llm = llm.with_structured_output(Classification)
        classification = structured_llm.invoke(
            classifier_prompt.format_messages(query=state["query"])
        )

        return {
            **state,
            "classification": classification,
            "trace": add_trace(
                state,
                "classifier_agent",
                classification.model_dump(),
            ),
        }

    def retrieval_agent(state: SupportState) -> SupportState:
        classification = state["classification"]
        top_k = state.get("top_k", 3)
        search_query = (
            f"Intent: {classification.intent}. "
            f"Priority: {classification.priority}. "
            f"Issue summary: {classification.summary}. "
            f"Original customer message: {state['query']}"
        )

        docs = vector_store.similarity_search(search_query, k=top_k)
        passages = [
            {
                "article_id": doc.metadata.get("article_id", "UNKNOWN"),
                "title": doc.metadata.get("title", "Untitled Article"),
                "intent": doc.metadata.get("intent", "general"),
                "passage": doc.page_content,
            }
            for doc in docs
        ]

        return {
            **state,
            "retrieved_passages": passages,
            "trace": add_trace(
                state,
                "retrieval_agent",
                {
                    "search_query": search_query,
                    "top_k": top_k,
                    "passages": passages,
                },
            ),
        }

    def composer_agent(state: SupportState) -> SupportState:
        classification = state["classification"].model_dump()
        kb_context = "\n\n".join(
            [
                f"Title: {item['title']}\nPassage: {item['passage']}"
                for item in state["retrieved_passages"]
            ]
        )

        draft_response = llm.invoke(
            composer_prompt.format_messages(
                query=state["query"],
                classification=json.dumps(classification, indent=2),
                kb_context=kb_context,
            )
        ).content

        final_response = llm.invoke(
            finalizer_prompt.format_messages(draft_response=draft_response)
        ).content

        return {
            **state,
            "draft_response": draft_response,
            "final_response": final_response,
            "trace": add_trace(
                state,
                "composer_agent",
                {
                    "draft_response": draft_response,
                    "final_response": final_response,
                },
            ),
        }

    graph = StateGraph(SupportState)
    graph.add_node("classifier_agent", classifier_agent)
    graph.add_node("retrieval_agent", retrieval_agent)
    graph.add_node("composer_agent", composer_agent)

    graph.set_entry_point("classifier_agent")
    graph.add_edge("classifier_agent", "retrieval_agent")
    graph.add_edge("retrieval_agent", "composer_agent")
    graph.add_edge("composer_agent", END)

    return graph.compile()


def build_result_payload(sample_number: int, result: SupportState) -> dict:
    return {
        "sample_number": sample_number,
        "customer_query": result["query"],
        "classification_result": result["classification"].model_dump(),
        "retrieved_kb_passages": [
            {
                "rank": index,
                "article_id": passage["article_id"],
                "title": passage["title"],
                "intent": passage["intent"],
                "passage": passage["passage"],
            }
            for index, passage in enumerate(result["retrieved_passages"], start=1)
        ],
        "draft_response_generation": result["draft_response"],
        "final_customer_facing_response": result["final_response"],
        "agent_execution_trace": result["trace"],
    }


def print_result(payload: dict) -> None:
    print("=" * 100)
    print(f"CUSTOMER SUPPORT TRIAGE RESULT - SAMPLE {payload['sample_number']}")
    print("=" * 100)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY before running this script.")

    base_dir = Path(__file__).resolve().parent
    kb_path = base_dir / "support_kb.txt"

    llm = ChatAnthropic(
        model=os.environ.get("CLAUDE_MODEL"),
        temperature=0,
        base_url=os.environ.get("ENDPOINT")
    )
    vector_store = build_vector_store(kb_path)
    support_graph = build_graph(llm, vector_store)
    structured_results = []

    for index, query in enumerate(SAMPLE_QUERIES, start=1):
        result = support_graph.invoke(
            {
                "query": query,
                "top_k": 3,
                "trace": [],
            }
        )
        payload = build_result_payload(index, result)
        structured_results.append(payload)
        print_result(payload)

    output_path = base_dir / "triage_results.json"
    output_path.write_text(
        json.dumps(structured_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Structured results saved to: {output_path}")


if __name__ == "__main__":
    main()