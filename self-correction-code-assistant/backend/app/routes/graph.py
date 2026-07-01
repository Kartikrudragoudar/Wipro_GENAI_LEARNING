"""Routes for the LangGraph agent workflow with cached state."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4

from app.provider_factory import create_ai_provider, create_embedding_store
from app.workflow_cache import (
    get_cache_stats,
    get_workflow_state,
    save_workflow_state,
    get_checkpoint,
    list_checkpoints,
)

router = APIRouter(prefix="/api", tags=["agent-workflow"])

_provider = create_ai_provider()
_embedding_store = create_embedding_store()


class AgentAnalyzeRequest(BaseModel):
    code: str
    language: str
    error_message: str
    user_context: str | None = None


class AgentSelfCorrectRequest(BaseModel):
    session_id: str
    feedback: str


class AgentBranchRequest(BaseModel):
    session_id: str
    attempt_number: int


@router.post("/agent/analyze")
def agent_analyze(request: AgentAnalyzeRequest):
    """Run the full analysis agent graph. State is cached for later self-correction."""
    try:
        from app.graph_engine import run_analysis_agent

        result = run_analysis_agent(request.model_dump(), _provider, embedding_store=_embedding_store)
        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])
        return {
            "session_id": result["session_id"],
            "analysis": result["analysis"],
            "fixed_code": result["fixed_code"],
            "explanation": result["explanation"],
            "confidence_score": result["confidence_score"],
            "suggested_tests": result["suggested_tests"],
            "risks": result["risks"],
            "attempts": result["attempts"],
            "loop_trace": result["loop_trace"],
            "status": result["status"],
            "step": result["step"],
        }
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="LangGraph is not installed. Install langgraph to use agent endpoints.") from exc


@router.post("/agent/self-correct")
def agent_self_correct(request: AgentSelfCorrectRequest):
    """Resume the agent workflow from cache and run self-correction using feedback."""
    try:
        from app.graph_engine import run_self_correction_agent

        result = run_self_correction_agent(request.session_id, request.feedback, _provider)
        return {
            "session_id": result["session_id"],
            "analysis": result["analysis"],
            "fixed_code": result["fixed_code"],
            "explanation": result["explanation"],
            "confidence_score": result["confidence_score"],
            "suggested_tests": result["suggested_tests"],
            "risks": result["risks"],
            "attempts": result["attempts"],
            "loop_trace": result["loop_trace"],
            "status": result["status"],
            "step": result["step"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="LangGraph is not installed.") from exc


@router.get("/agent/state/{session_id}")
def get_agent_state(session_id: str):
    """Retrieve the cached agent workflow state for a session."""
    state = get_workflow_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No cached state for session {session_id}")
    return {
        "session_id": state["session_id"],
        "status": state["status"],
        "step": state["step"],
        "attempts_count": len(state["attempts"]),
        "loop_trace": state["loop_trace"],
    }


@router.get("/agent/cache/stats")
def cache_stats():
    """Return workflow cache utilization."""
    return get_cache_stats()


@router.get("/agent/checkpoints/{session_id}")
def get_session_checkpoints(session_id: str):
    """List all checkpoint snapshots for a session."""
    checkpoints = list_checkpoints(session_id)
    if not checkpoints:
        raise HTTPException(status_code=404, detail=f"No checkpoints for session {session_id}")
    return {"session_id": session_id, "checkpoints": checkpoints}


@router.get("/agent/checkpoint/{session_id}/{attempt}")
def get_session_checkpoint(session_id: str, attempt: int):
    """Retrieve a specific checkpoint snapshot."""
    cp = get_checkpoint(session_id, attempt)
    if not cp:
        raise HTTPException(
            status_code=404,
            detail=f"No checkpoint for session {session_id} attempt {attempt}",
        )
    return cp


@router.post("/agent/multi-analyze")
def agent_multi_analyze(request: AgentAnalyzeRequest):
    """Run the 4-agent pipeline (Analyzer → Fix Generator → Reviewer → Test Suggester).

    Returns all standard fields plus reviewer_verdict, test_suite, lint_output,
    and tool_calls_trace.
    """
    try:
        from app.multi_agent_engine import run_multi_agent

        result = run_multi_agent(request.model_dump(), _provider, embedding_store=_embedding_store)
        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])
        return {
            "session_id": result["session_id"],
            "analysis": result["analysis"],
            "fixed_code": result["fixed_code"],
            "explanation": result["explanation"],
            "confidence_score": result["confidence_score"],
            "suggested_tests": result["suggested_tests"],
            "risks": result["risks"],
            "attempts": result["attempts"],
            "loop_trace": result["loop_trace"],
            "status": result["status"],
            "step": result["step"],
            "reviewer_verdict": result.get("reviewer_verdict"),
            "test_suite": result.get("test_suite"),
            "lint_output": result.get("lint_output"),
            "tool_calls_trace": result.get("tool_calls_trace", []),
        }
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="LangGraph is not installed. Install langgraph to use agent endpoints.") from exc


@router.post("/agent/branch")
def branch_from_checkpoint(request: AgentBranchRequest):
    """Create a new session by branching from a checkpoint snapshot."""
    cp = get_checkpoint(request.session_id, request.attempt_number)
    if not cp:
        raise HTTPException(
            status_code=404,
            detail=f"No checkpoint for session {request.session_id} attempt {request.attempt_number}",
        )
    new_session_id = str(uuid4())
    cp["session_id"] = new_session_id
    cp["loop_trace"]["branched_from"] = {
        "original_session_id": request.session_id,
        "attempt_number": request.attempt_number,
    }
    save_workflow_state(new_session_id, cp)
    return {"new_session_id": new_session_id, "branched_from": request.session_id, "attempt": request.attempt_number}