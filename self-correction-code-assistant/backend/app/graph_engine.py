"""LangGraph-based agent engine for the correction loop.

Models the correction workflow as a state graph with cached state between steps:

    input_node -> analysis_node -> correction_node -> [WAIT for user feedback]
                                                          |
                            [user resumes] -> validation_node -> self_correction_node -> done

The workflow state is cached between user interactions so the agent can resume
from where it left off when the user provides feedback.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph

from app.ai_provider import AIProvider
from app.models import (
    AnalyzeRequest,
    AttemptStatus,
    CorrectionAttempt,
    LoopStatus,
    LoopTrace,
    SelfCorrectRequest,
)
from app.workflow_cache import save_workflow_state, get_workflow_state, save_checkpoint

logger = logging.getLogger(__name__)

_MAX_REANALYSIS_ATTEMPTS = 3


class AgentState(TypedDict):
    """State passed between graph nodes and persisted in cache."""
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
    step: str  # tracks which node was last completed
    similar_corrections: list[dict[str, Any]]  # cache-warmed from embeddings


def build_analysis_graph(provider: AIProvider, embedding_store=None) -> StateGraph:
    """Build the LangGraph for the initial analysis + correction pass.

    Args:
        provider: The AI provider for analysis/correction.
        embedding_store: Optional CorrectionEmbeddingStore for cache warming.
    """

    def input_node(state: AgentState) -> AgentState:
        """Validate input, start session, and warm cache from embeddings."""
        req = state["request"]
        if not req.get("code", "").strip():
            state["error"] = "Code is required."
            state["status"] = "error"
            return state
        state["session_id"] = str(uuid4())
        state["loop_trace"]["input_received"] = True
        state["status"] = LoopStatus.ANALYZING.value
        state["step"] = "input"

        # Cache warming: find similar past corrections from embeddings
        if embedding_store is not None:
            try:
                similar = embedding_store.find_similar_corrections(
                    language=req.get("language", ""),
                    error_message=req.get("error_message", ""),
                    code_snippet=req.get("code", ""),
                    top_k=3,
                )
                state["similar_corrections"] = similar
                state["loop_trace"]["cache_warmed"] = len(similar)
                logger.info("Agent: cache warmed with %d similar corrections", len(similar))
            except Exception:
                logger.warning("Agent: cache warming failed, continuing without", exc_info=True)
                state["similar_corrections"] = []
        else:
            state["similar_corrections"] = []

        logger.info("Agent: input validated, session=%s", state["session_id"])
        return state

    def analysis_node(state: AgentState) -> AgentState:
        """Run AI analysis on the code, enriched with similar past corrections."""
        req = state["request"]
        # Enrich user_context with similar corrections if available
        extra_context = req.get("user_context") or ""
        similar = state.get("similar_corrections", [])
        if similar:
            hints = "; ".join(
                m.get("document", "") for m in similar[:3] if m.get("document")
            )
            if hints:
                extra_context = f"{extra_context}\n[Similar past fixes: {hints}]".strip()
        request = AnalyzeRequest(
            code=req["code"],
            language=req["language"],
            error_message=req["error_message"],
            user_context=extra_context or None,
        )
        analysis = provider.analyze_code(request)
        state["analysis"] = analysis.model_dump()
        state["loop_trace"]["analysis_completed"] = True
        state["step"] = "analysis"
        logger.info("Agent: analysis complete")
        return state

    def correction_node(state: AgentState) -> AgentState:
        """Generate the fix using the analysis."""
        req = state["request"]
        from app.models import CorrectionAnalysis
        analysis = CorrectionAnalysis(**state["analysis"])
        request = AnalyzeRequest(
            code=req["code"],
            language=req["language"],
            error_message=req["error_message"],
            user_context=req.get("user_context"),
        )
        fixed_code, explanation, confidence, tests = provider.generate_fix(request, analysis)
        state["fixed_code"] = fixed_code
        state["explanation"] = explanation
        state["confidence_score"] = confidence
        state["suggested_tests"] = tests
        state["risks"] = analysis.risks
        state["loop_trace"]["correction_generated"] = True
        state["status"] = LoopStatus.FIX_GENERATED.value
        state["step"] = "correction"

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

        # Cache state and save checkpoint
        save_workflow_state(state["session_id"], state)
        save_checkpoint(state["session_id"], attempt.attempt_number, state)
        logger.info("Agent: correction complete, state cached for session=%s", state["session_id"])
        return state

    def route_by_confidence(state: AgentState) -> str:
        """Route based on confidence score after correction."""
        confidence = state.get("confidence_score", 0.0)
        num_attempts = len(state.get("attempts", []))

        # Guard against infinite re-analysis loops
        if num_attempts >= _MAX_REANALYSIS_ATTEMPTS:
            logger.info("Agent: max re-analysis attempts (%d) reached, ending", _MAX_REANALYSIS_ATTEMPTS)
            return "end"

        if confidence >= 0.9:
            state["loop_trace"]["high_confidence_exit"] = True
            logger.info("Agent: high confidence (%.2f), ending", confidence)
            return "end"
        elif confidence < 0.4:
            state["loop_trace"]["auto_reanalyzed"] = True
            logger.info("Agent: low confidence (%.2f), re-analyzing", confidence)
            return "re_analyze"
        else:
            return "end"

    graph = StateGraph(AgentState)
    graph.add_node("input", input_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("correction", correction_node)

    graph.set_entry_point("input")
    graph.add_edge("input", "analysis")
    graph.add_edge("analysis", "correction")
    graph.add_conditional_edges(
        "correction",
        route_by_confidence,
        {"end": END, "re_analyze": "analysis"},
    )

    return graph


def build_self_correction_graph(provider: AIProvider) -> StateGraph:
    """Build the LangGraph for the self-correction pass (resumes from cached state)."""

    def validation_node(state: AgentState) -> AgentState:
        """Process validation feedback."""
        feedback = state.get("feedback", "")
        state["loop_trace"]["validation_feedback_received"] = True
        state["status"] = LoopStatus.SELF_CORRECTING.value
        state["step"] = "validation"
        logger.info("Agent: validation feedback received")
        return state

    def self_correction_node(state: AgentState) -> AgentState:
        """Generate improved fix using feedback + previous attempts."""
        req = state["request"]
        last_attempt = state["attempts"][-1] if state["attempts"] else {}
        feedback = state.get("feedback", "")

        sc_request = SelfCorrectRequest(
            session_id=state["session_id"],
            original_code=req["code"],
            previous_fixed_code=last_attempt.get("fixed_code", req["code"]),
            language=req["language"],
            test_output=feedback,
            user_feedback=feedback,
            attempt_number=len(state["attempts"]),
            previous_attempts=[],
        )

        analysis, fixed_code, explanation, confidence, tests = provider.self_correct(sc_request)
        state["analysis"] = analysis.model_dump()
        state["fixed_code"] = fixed_code
        state["explanation"] = explanation
        state["confidence_score"] = confidence
        state["suggested_tests"] = tests
        state["risks"] = analysis.risks
        state["loop_trace"]["self_correction_completed"] = True
        state["status"] = LoopStatus.NEEDS_ANOTHER_LOOP.value
        state["step"] = "self_correction"

        attempt = CorrectionAttempt(
            attempt_number=len(state["attempts"]) + 1,
            timestamp=datetime.now(timezone.utc),
            status=AttemptStatus.IMPROVED,
            bug_summary=analysis.bug_summary,
            root_cause=analysis.root_cause,
            fixed_code=fixed_code,
            explanation=explanation,
            confidence_score=confidence,
            change_summary=provider.summarize_attempt_change(
                last_attempt.get("fixed_code", req["code"]), fixed_code
            ),
        )
        state["attempts"].append(attempt.model_dump())

        # Update cache and save checkpoint
        save_workflow_state(state["session_id"], state)
        save_checkpoint(state["session_id"], attempt.attempt_number, state)
        logger.info("Agent: self-correction complete, attempt %d cached", attempt.attempt_number)
        return state

    graph = StateGraph(AgentState)
    graph.add_node("validation", validation_node)
    graph.add_node("self_correction", self_correction_node)

    graph.set_entry_point("validation")
    graph.add_edge("validation", "self_correction")
    graph.add_edge("self_correction", END)

    return graph


def run_analysis_agent(
    request_dict: dict[str, Any],
    provider: AIProvider,
    embedding_store=None,
) -> AgentState:
    """Execute the analysis graph and return the final state (also cached).

    Args:
        request_dict: The analysis request data.
        provider: The AI provider.
        embedding_store: Optional embedding store for cache warming.
    """
    graph = build_analysis_graph(provider, embedding_store=embedding_store)
    compiled = graph.compile()

    initial_state: AgentState = {
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
        },
        "status": LoopStatus.WAITING_FOR_INPUT.value,
        "error": None,
        "feedback": None,
        "step": "init",
        "similar_corrections": [],
    }

    return compiled.invoke(initial_state)


def run_self_correction_agent(session_id: str, feedback: str, provider: AIProvider) -> AgentState:
    """Resume the agent workflow from cache and run self-correction."""
    cached_state = get_workflow_state(session_id)
    if not cached_state:
        raise ValueError(f"No cached workflow state for session {session_id}. Start a new analysis first.")

    cached_state["feedback"] = feedback

    graph = build_self_correction_graph(provider)
    compiled = graph.compile()

    return compiled.invoke(cached_state)
