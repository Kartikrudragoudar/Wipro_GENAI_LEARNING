import os
import uuid
import json
from pathlib import Path

import requests
import chromadb
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

load_dotenv()

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True)
Path("chroma_db").mkdir(exist_ok=True)

API_KEY = os.getenv("ANTHROPIC_API_KEY")
ENDPOINT = "https://llmgw-wp.tekstac.com/v1/chat/completions"

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="rag_documents")


def read_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def read_pdf_file(file_path):
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def extract_text(file_path):
    suffix = Path(file_path).suffix.lower()
    if suffix == ".txt":
        return read_text_file(file_path)
    if suffix == ".pdf":
        return read_pdf_file(file_path)
    raise ValueError("Only .txt and .pdf files are supported")


def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def store_document_chunks(chunks, source_name):
    embeddings = embedding_model.encode(chunks).tolist()
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": source_name, "chunk_index": index} for index, _ in enumerate(chunks)]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )


def ingest_existing_files():
    existing_sources = set()
    current_data = collection.get(include=["metadatas"])

    for metadata in current_data.get("metadatas", []):
        if metadata and "source" in metadata:
            existing_sources.add(metadata["source"])

    upload_folder = Path(app.config["UPLOAD_FOLDER"])

    for file_path in upload_folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in [".txt", ".pdf"]:
            if file_path.name in existing_sources:
                continue

            text = extract_text(file_path)
            chunks = chunk_text(text)

            if chunks:
                store_document_chunks(chunks, file_path.name)


def retrieve_context(question, top_k=3):
    query_embedding = embedding_model.encode([question]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    context_parts = []
    matches = []

    for metadata, document, distance in zip(metadatas, documents, distances):
        source = metadata.get("source", "unknown")
        chunk_index = metadata.get("chunk_index", -1)

        context_parts.append(f"Source: {source} | Chunk: {chunk_index}\n{document}")
        matches.append({
            "source": source,
            "chunk_index": chunk_index,
            "distance": distance,
            "content": document
        })

    return "\n\n".join(context_parts), matches


def ask_llm(question, context):
    prompt = f"""
You are a beginner-friendly GenAI training assistant.
Answer clearly and simply using only the provided context.
If the answer is not present in the context, say:
"I could not find that in the training content."

Context:
{context}

Question:
{question}
"""

    payload = {
        "model": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "max_tokens": 500,
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(ENDPOINT, headers=headers, json=payload)
    response_data = response.json()

    assistant_reply = response_data["choices"][0]["message"]["content"]
    return assistant_reply, response_data


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if collection.count() == 0:
        return jsonify({"error": "No indexed documents found in uploads folder."}), 400

    try:
        context, matches = retrieve_context(question, top_k=3)
        answer, llm_response = ask_llm(question, context)

        return jsonify({
            "question": question,
            "retrieved_context": context,
            "matches": matches,
            "llm_full_response": llm_response,
            "answer": answer
        })
    except Exception as error:
        return jsonify({"error": str(error)}), 500


if __name__ == "__main__":
    ingest_existing_files()
    app.run(debug=True)