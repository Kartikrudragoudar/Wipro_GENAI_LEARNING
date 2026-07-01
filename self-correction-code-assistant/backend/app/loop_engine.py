from datetime import datetime, timezone
from uuid import uuid4

from app.ai_provider import AIProvider
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AttemptStatus,
    CorrectionAnalysis,
    CorrectionAttempt,
    LoopStatus,
    LoopTrace,
    LoopTraceRequest,
    SelfCorrectRequest,
    SelfCorrectResponse,
)


class LoopEngine:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def validate_input(self, request: AnalyzeRequest) -> None:
        if not request.code.strip():
            raise ValueError("Code is required to start the input loop.")
        if not request.error_message.strip():
            raise ValueError("An error message or issue description is required.")

    def run_analysis_loop(self, request: AnalyzeRequest) -> CorrectionAnalysis:
        self.validate_input(request)
        return self.provider.analyze_code(request)

    def run_correction_loop(self, request: AnalyzeRequest, analysis: CorrectionAnalysis) -> tuple[str, str, float, list[str]]:
        return self.provider.generate_fix(request, analysis)

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        session_id = str(uuid4())
        analysis = self.run_analysis_loop(request)
        fixed_code, explanation, confidence_score, suggested_tests = self.run_correction_loop(request, analysis)
        attempt = CorrectionAttempt(
            attempt_number=1,
            timestamp=datetime.now(timezone.utc),
            status=AttemptStatus.GENERATED,
            bug_summary=analysis.bug_summary,
            root_cause=analysis.root_cause,
            fixed_code=fixed_code,
            explanation=explanation,
            confidence_score=confidence_score,
            change_summary=self.provider.summarize_attempt_change(request.code, fixed_code),
        )
        loop_trace = self.build_loop_trace(
            LoopTraceRequest(has_input=True, has_analysis=True, has_fix=True)
        )
        return AnalyzeResponse(
            session_id=session_id,
            bug_summary=analysis.bug_summary,
            root_cause=analysis.root_cause,
            fixed_code=fixed_code,
            explanation=explanation,
            confidence_score=confidence_score,
            suggested_tests=suggested_tests,
            risks=analysis.risks,
            attempts=[attempt],
            loop_trace=loop_trace,
        )

    def run_validation_loop(self, request: SelfCorrectRequest) -> LoopStatus:
        feedback = f"{request.test_output or ''} {request.user_feedback or ''}".lower()
        if any(token in feedback for token in ["pass", "success", "fixed", "green"]):
            return LoopStatus.CORRECTION_COMPLETE
        if any(token in feedback for token in ["fail", "error", "traceback", "exception", "undefined"]):
            return LoopStatus.NEEDS_ANOTHER_LOOP
        return LoopStatus.AWAITING_VALIDATION_FEEDBACK

    def run_self_correction_loop(self, request: SelfCorrectRequest) -> SelfCorrectResponse:
        validation_status = self.run_validation_loop(request)
        analysis, fixed_code, explanation, confidence_score, suggested_tests = self.provider.self_correct(request)
        next_attempt_number = request.attempt_number + 1
        attempt_status = AttemptStatus.VALIDATED if validation_status == LoopStatus.CORRECTION_COMPLETE else AttemptStatus.IMPROVED
        attempt = CorrectionAttempt(
            attempt_number=next_attempt_number,
            timestamp=datetime.now(timezone.utc),
            status=attempt_status,
            bug_summary=analysis.bug_summary,
            root_cause=analysis.root_cause,
            fixed_code=fixed_code,
            explanation=explanation,
            confidence_score=confidence_score,
            change_summary=self.provider.summarize_attempt_change(request.previous_fixed_code, fixed_code),
        )
        attempts = [*request.previous_attempts, attempt]
        loop_trace = self.build_loop_trace(
            LoopTraceRequest(
                session_id=request.session_id,
                has_input=True,
                has_analysis=True,
                has_fix=True,
                has_feedback=True,
                has_self_correction=True,
            )
        )
        loop_trace.final_status = validation_status
        return SelfCorrectResponse(
            session_id=request.session_id,
            attempt=attempt,
            attempts=attempts,
            loop_trace=loop_trace,
            suggested_tests=suggested_tests,
            risks=analysis.risks,
        )

    def build_loop_trace(self, request: LoopTraceRequest) -> LoopTrace:
        final_status = LoopStatus.WAITING_FOR_INPUT
        if request.has_self_correction:
            final_status = LoopStatus.NEEDS_ANOTHER_LOOP
        elif request.has_feedback:
            final_status = LoopStatus.SELF_CORRECTING
        elif request.has_fix:
            final_status = LoopStatus.FIX_GENERATED
        elif request.has_analysis:
            final_status = LoopStatus.ANALYZING
        elif request.has_input:
            final_status = LoopStatus.WAITING_FOR_INPUT

        return LoopTrace(
            input_received=request.has_input,
            analysis_completed=request.has_analysis,
            correction_generated=request.has_fix,
            validation_feedback_received=request.has_feedback,
            self_correction_completed=request.has_self_correction,
            final_status=final_status,
        )
