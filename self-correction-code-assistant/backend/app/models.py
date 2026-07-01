from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


Language = Literal["Python", "JavaScript", "TypeScript", "Java", "C++"]


class AttemptStatus(str, Enum):
    GENERATED = "generated"
    VALIDATED = "validated"
    FAILED = "failed"
    IMPROVED = "improved"
    NEEDS_REVIEW = "needs_review"


class LoopStatus(str, Enum):
    WAITING_FOR_INPUT = "waiting_for_input"
    ANALYZING = "analyzing"
    FIX_GENERATED = "fix_generated"
    AWAITING_VALIDATION_FEEDBACK = "awaiting_validation_feedback"
    SELF_CORRECTING = "self_correcting"
    CORRECTION_COMPLETE = "correction_complete"
    NEEDS_ANOTHER_LOOP = "needs_another_loop"


class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Language
    error_message: str = Field(..., min_length=1)
    user_context: str | None = None


class CorrectionAnalysis(BaseModel):
    bug_summary: str
    root_cause: str
    fix_strategy: str
    risks: list[str]


class CorrectionAttempt(BaseModel):
    attempt_number: int = Field(..., ge=1)
    timestamp: datetime
    status: AttemptStatus
    bug_summary: str
    root_cause: str
    fixed_code: str
    explanation: str
    confidence_score: float = Field(..., ge=0, le=1)
    change_summary: str


class LoopTrace(BaseModel):
    input_received: bool = False
    analysis_completed: bool = False
    correction_generated: bool = False
    validation_feedback_received: bool = False
    self_correction_completed: bool = False
    final_status: LoopStatus = LoopStatus.WAITING_FOR_INPUT


class AnalyzeResponse(BaseModel):
    session_id: str
    bug_summary: str
    root_cause: str
    fixed_code: str
    explanation: str
    confidence_score: float = Field(..., ge=0, le=1)
    suggested_tests: list[str]
    risks: list[str]
    attempts: list[CorrectionAttempt]
    loop_trace: LoopTrace


class SelfCorrectRequest(BaseModel):
    session_id: str
    original_code: str = Field(..., min_length=1)
    previous_fixed_code: str = Field(..., min_length=1)
    language: Language
    test_output: str | None = None
    user_feedback: str | None = None
    attempt_number: int = Field(..., ge=1)
    previous_attempts: list[CorrectionAttempt] = Field(default_factory=list)


class SelfCorrectResponse(BaseModel):
    session_id: str
    attempt: CorrectionAttempt
    attempts: list[CorrectionAttempt]
    loop_trace: LoopTrace
    suggested_tests: list[str]
    risks: list[str]


class LoopTraceRequest(BaseModel):
    session_id: str | None = None
    has_input: bool = False
    has_analysis: bool = False
    has_fix: bool = False
    has_feedback: bool = False
    has_self_correction: bool = False


class SampleBug(BaseModel):
    id: str
    title: str
    language: Language
    code: str
    error_message: str
    user_context: str


class HealthResponse(BaseModel):
    status: str
    service: str
    provider: str


# --- Multi-agent models ---


class ReviewVerdict(BaseModel):
    passed: bool
    issues: list[str]
    reviewer_confidence: float = Field(..., ge=0, le=1)
    recommendation: Literal["accept", "revise", "reject"]
    lint_output: str | None = None


class TestSuiteOutput(BaseModel):
    tests: list[str]
    test_strategy: str
    coverage_notes: str
