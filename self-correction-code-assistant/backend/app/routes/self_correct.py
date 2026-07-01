from fastapi import APIRouter, HTTPException

from app.loop_engine import LoopEngine
from app.models import SelfCorrectRequest, SelfCorrectResponse
from app.provider_factory import create_ai_provider, create_embedding_store

router = APIRouter(prefix="/api", tags=["self-correction"])

_provider = create_ai_provider()
_embedding_store = create_embedding_store()
engine = LoopEngine(_provider)


@router.post("/self-correct", response_model=SelfCorrectResponse)
def self_correct(request: SelfCorrectRequest) -> SelfCorrectResponse:
    if not (request.test_output or request.user_feedback):
        raise HTTPException(status_code=422, detail="Validation feedback is required for self-correction.")
    result = engine.run_self_correction_loop(request)
    if _embedding_store and result.attempt:
        _embedding_store.store_correction(
            session_id=result.session_id,
            language=request.language,
            error_message=request.test_output or request.user_feedback or "",
            bug_summary=result.attempt.bug_summary,
            fix_strategy=result.attempt.root_cause,
            fixed_code=result.attempt.fixed_code,
            attempt=result.attempt,
        )
    return result
