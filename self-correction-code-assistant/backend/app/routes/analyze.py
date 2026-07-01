from fastapi import APIRouter, HTTPException

from app.loop_engine import LoopEngine
from app.models import AnalyzeRequest, AnalyzeResponse
from app.provider_factory import create_ai_provider, create_embedding_store

router = APIRouter(prefix="/api", tags=["analysis"])

_provider = create_ai_provider()
_embedding_store = create_embedding_store()
engine = LoopEngine(_provider)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_code(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = engine.analyze(request)
        if _embedding_store and result.attempts:
            attempt = result.attempts[0]
            _embedding_store.store_correction(
                session_id=result.session_id,
                language=request.language,
                error_message=request.error_message,
                bug_summary=result.bug_summary,
                fix_strategy=result.root_cause,
                fixed_code=result.fixed_code,
                attempt=attempt,
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
