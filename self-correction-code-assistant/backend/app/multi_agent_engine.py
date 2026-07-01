"""Multi-agent correction engine using LangGraph.

Four specialized agents form a pipeline:

    input_node
        └─► analyzer_node     (tools: search_similar_fixes, get_session_history)
                └─► fix_generator_node
                        └─► reviewer_node  (tools: lint_code, read_checkpoint)
                                ├─► [passed / max retries] ─► test_suggester_node  (tools: store_correction)
                                │                                     └─► END
                                └─► [failed] ─► fix_generator_node  (up to 2 revise cycles)

State is persisted to SQLite after each fix generation (checkpoint + workflow cache).
All existing single-agent graph behaviour in graph_engine.py is unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph

from app.agent_tools import (
    call_tool,
    make_analyzer_tools,
    make_reviewer_tools,
    make_test_suggester_tools,
    run_lint,
)
from app.ai_provider import AIProvider
from app.models import (
    AnalyzeRequest,
    AttemptStatus,
    CorrectionAttempt,
    LoopStatus,
    SelfCorrectRequest,
)
from app.workflow_cache import save_checkpoint, save_workflow_state

logger = logging.getLogger(__name__)

_MAX_REVISE_CYCLES = 2


class MultiAgentState(TypedDict):
    """Extended agent state for the multi-agent pipeline."""
    # --- Inherited from single-agent graph ---
    session_id: str
    request: dict[str, Any]
    analysis: dict[str, Any] | None
    fixed_code: str | None
    explanation: str | None
    confidence_score: float
    suggested_tests: list[str]
    risks: list[str]
    attempts: list[dict[str, Any]]
    loop_trace: dict[str, Any]
    status: str
    error: str | None
    feedback: str | None
    step: str
    similar_corrections: list[dict[str, Any]]
    # --- Multi-agent specific ---
    reviewer_verdict: dict[str, Any] | None
    test_suite: dict[str, Any] | None
    review_passed: bool
    revise_count: int
    lint_output: str | None
    tool_calls_trace: list[str]


def build_multi_agent_graph(provider: AIProvider, embedding_store=None) -> StateGraph:
    """Build the 4-node multi-agent LangGraph.

    Args:
        provider: AI provider implementing analyze_code, generate_fix,
                  review_fix, suggest_tests.
        embedding_store: Optional CorrectionEmbeddingStore for tool usage.
    """
    analyzer_tools = make_analyzer_tools(embedding_store)
    reviewer_tools = make_reviewer_tools(embedding_store)
    test_tools = make_test_suggester_tools(embedding_store)

    # ------------------------------------------------------------------
    # Node 1 — input
    # ------------------------------------------------------------------

    def input_node(state: MultiAgentState) -> MultiAgentState:
        """Validate input and assign session id."""
        req = state["request"]
        if not req.get("code", "").strip():
            state["error"] = "Code is required."
            state["status"] = "error"
            return state
        state["session_id"] = str(uuid4())
        state["loop_trace"]["input_received"] = True
        state["status"] = LoopStatus.ANALYZING.value
        state["step"] = "input"
        logger.info("MultiAgent: input validated, session=%s", state["session_id"])
        return state

    # ------------------------------------------------------------------
    # Node 2 — analyzer  (uses search_similar_fixes + get_session_history)
    # ------------------------------------------------------------------

    def analyzer_node(state: MultiAgentState) -> MultiAgentState:
        """Run AI analysis, enriched with similar past corrections via tools."""
        req = state["request"]

        # Tool call: search for similar fixes
        similar_raw = call_tool(
            analyzer_tools,
            "search_similar_fixes",
            {
                "language": req.get("language", ""),
                "error_message": req.get("error_message", ""),
                "code_snippet": req.get("code", "")[:300],
            },
        )
        state["tool_calls_trace"].append("search_similar_fixes")

        import json
        try:
            similar = json.loads(similar_raw)
        except Exception:
            similar = []
        state["similar_corrections"] = similar

        # Build enriched user_context
        extra_context = req.get("user_context") or ""
        hints = "; ".join(
            m.get("document", "") for m in similar[:3] if m.get("document")
        )
        if hints:
            extra_context = f"{extra_context}\n[Similar past fixes: {hints}]".strip()

        analysis_req = AnalyzeRequest(
            code=req["code"],
            language=req["language"],
            error_message=req["error_message"],
            user_context=extra_context or None,
        )
        analysis = provider.analyze_code(analysis_req)
        state["analysis"] = analysis.model_dump()
        state["loop_trace"]["analysis_completed"] = True
        state["step"] = "analyzer"
        logger.info("MultiAgent: analysis complete")
        return state

    # ------------------------------------------------------------------
    # Node 3 — fix_generator
    # ------------------------------------------------------------------

    def fix_generator_node(state: MultiAgentState) -> MultiAgentState:
        """Generate the fix using the analysis. Saves a checkpoint per attempt."""
        req = state["request"]
        from app.models import CorrectionAnalysis

        analysis = CorrectionAnalysis(**state["analysis"])
        analysis_req = AnalyzeRequest(
            code=req["code"],
            language=req["language"],
            error_message=req["error_message"],
            user_context=req.get("user_context"),
        )
        fixed_code, explanation, confidence, tests = provider.generate_fix(analysis_req, analysis)

        state["fixed_code"] = fixed_code
        state["explanation"] = explanation
        state["confidence_score"] = confidence
        state["suggested_tests"] = tests
        state["risks"] = analysis.risks
        state["loop_trace"]["correction_generated"] = True
        state["status"] = LoopStatus.FIX_GENERATED.value
        state["step"] = "fix_generator"

        attempt = CorrectionAttempt(
            attempt_number=len(state["attempts"]) + 1,
            timestamp=datetime.now(timezone.utc),
            status=AttemptStatus.GENERATED,
            bug_summary=analysis.bug_summary,
            root_cause=analysis.root_cause,
            fixed_code=fixed_code,
            explanation=explanation,
            confidence_score=confidence,
            change_summary=provider.summarize_attempt_change(req["code"], fixed_code),
        )
        state["attempts"].append(attempt.model_dump())

        save_workflow_state(state["session_id"], state)
        save_checkpoint(state["session_id"], attempt.attempt_number, state)
        logger.info("MultiAgent: fix generated, attempt=%d", attempt.attempt_number)
        return state

    # ------------------------------------------------------------------
    # Node 4 — reviewer  (uses lint_code + read_checkpoint)
    # ------------------------------------------------------------------

    def reviewer_node(state: MultiAgentState) -> MultiAgentState:
        """Review the fix using lint + AI reviewer. Updates review_passed."""
        req = state["request"]
        fixed_code = state.get("fixed_code") or ""

        # Tool call: lint the proposed fix
        lint_result = call_tool(
            reviewer_tools,
            "lint_code",
            {"code": fixed_code, "language": req.get("language", "")},
        )
        state["lint_output"] = lint_result if lint_result else None
        state["tool_calls_trace"].append("lint_code")

        from app.models import CorrectionAnalysis
        analysis = CorrectionAnalysis(**state["analysis"])
        analysis_req = AnalyzeRequest(
            code=req["code"],
            language=req["language"],
            error_message=req["error_message"],
            user_context=req.get("user_context"),
        )

        verdict = provider.review_fix(
            analysis_req,
            analysis,
            fixed_code,
            lint_output=lint_result or None,
        )
        state["reviewer_verdict"] = verdict.model_dump()
        state["review_passed"] = verdict.passed
        state["loop_trace"]["reviewer_verdict"] = verdict.recommendation
        state["step"] = "reviewer"

        if not verdict.passed:
            state["revise_count"] = state.get("revise_count", 0) + 1

        logger.info(
            "MultiAgent: reviewer verdict=%s, passed=%s, revise_count=%d",
            verdict.recommendation,
            verdict.passed,
            state.get("revise_count", 0),
        )
        return state

    # ------------------------------------------------------------------
    # Node 5 — test_suggester  (uses store_correction)
    # ------------------------------------------------------------------

    def test_suggester_node(state: MultiAgentState) -> MultiAgentState:
        """Generate a test suite and persist the correction to embeddings."""
        req = state["request"]
        from app.models import CorrectionAnalysis

        analysis = CorrectionAnalysis(**state["analysis"])
        analysis_req = AnalyzeRequest(
            code=req["code"],
            language=req["language"],
            error_message=req["error_message"],
            user_context=req.get("user_context"),
        )
        test_suite = provider.suggest_tests(analysis_req, analysis)
        state["test_suite"] = test_suite.model_dump()
        state["suggested_tests"] = test_suite.tests
        state["step"] = "test_suggester"
        state["status"] = LoopStatus.CORRECTION_COMPLETE.value

        # Tool call: persist correction to embedding store
        last_attempt = state["attempts"][-1] if state["attempts"] else {}
        call_tool(
            test_tools,
            "store_correction",
            {
                "session_id": state["session_id"],
                "language": req.get("language", ""),
                "error_message": req.get("error_message", ""),
                "bug_summary": analysis.bug_summary,
                "fix_strategy": analysis.fix_strategy,
                "fixed_code": state.get("fixed_code") or "",
                "attempt": last_attempt,
            },
        )
        state["tool_calls_trace"].append("store_correction")

        # Final state cache
        save_workflow_state(state["session_id"], state)
        logger.info("MultiAgent: test suite generated, correction stored in embeddings")
        return state

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_after_review(state: MultiAgentState) -> str:
        """Route to test_suggester if passed or max retries reached, else fix_generator."""
        if state.get("review_passed", False):
            return "test_suggester"
        if state.get("revise_count", 0) >= _MAX_REVISE_CYCLES:
            logger.info("MultiAgent: max revise cycles reached, proceeding to test_suggester")
            return "test_suggester"
        return "fix_generator"

    # ------------------------------------------------------------------
    # Graph wiring
    # ------------------------------------------------------------------

    graph = StateGraph(MultiAgentState)
    graph.add_node("input", input_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("fix_generator", fix_generator_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("test_suggester", test_suggester_node)

    graph.set_entry_point("input")
    graph.add_edge("input", "analyzer")
    graph.add_edge("analyzer", "fix_generator")
    graph.add_edge("fix_generator", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"fix_generator": "fix_generator", "test_suggester": "test_suggester"},
    )
    graph.add_edge("test_suggester", END)

    return graph


def run_multi_agent(
    request_dict: dict[str, Any],
    provider: AIProvider,
    embedding_store=None,
) -> MultiAgentState:
    """Execute the multi-agent graph and return the final state.

    Args:
        request_dict: The analysis request data (code, language, error_message, user_context).
        provider: The AI provider.
        embedding_store: Optional CorrectionEmbeddingStore for tool usage.
    """
    graph = build_multi_agent_graph(provider, embedding_store=embedding_store)
    compiled = graph.compile()

    initial_state: MultiAgentState = {
        "session_id": "",
        "request": request_dict,
        "analysis": None,
        "fixed_code": None,
        "explanation": None,
        "confidence_score": 0.0,
        "suggested_tests": [],
        "risks": [],
        "attempts": [],
        "loop_trace": {
            "input_received": False,
            "analysis_completed": False,
            "correction_generated": False,
            "validation_feedback_received": False,
            "self_correction_completed": False,
            "reviewer_verdict": None,
        },
        "status": LoopStatus.WAITING_FOR_INPUT.value,
        "error": None,
        "feedback": None,
        "step": "init",
        "similar_corrections": [],
        "reviewer_verdict": None,
        "test_suite": None,
        "review_passed": False,
        "revise_count": 0,
        "lint_output": None,
        "tool_calls_trace": [],
    }

    return compiled.invoke(initial_state)
