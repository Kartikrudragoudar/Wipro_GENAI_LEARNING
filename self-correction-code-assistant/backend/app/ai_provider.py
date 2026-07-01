from abc import ABC, abstractmethod

from app.models import AnalyzeRequest, CorrectionAnalysis, ReviewVerdict, SelfCorrectRequest, TestSuiteOutput


class AIProvider(ABC):
    @abstractmethod
    def analyze_code(self, request: AnalyzeRequest) -> CorrectionAnalysis:
        """Return structured bug analysis for the submitted code."""

    @abstractmethod
    def generate_fix(self, request: AnalyzeRequest, analysis: CorrectionAnalysis) -> tuple[str, str, float, list[str]]:
        """Return fixed code, explanation, confidence score, and suggested tests."""

    @abstractmethod
    def self_correct(self, request: SelfCorrectRequest) -> tuple[CorrectionAnalysis, str, str, float, list[str]]:
        """Return improved analysis and code using validation feedback."""

    @abstractmethod
    def summarize_attempt_change(self, previous_code: str, new_code: str) -> str:
        """Explain what changed from the previous correction attempt."""

    @abstractmethod
    def review_fix(
        self,
        request: AnalyzeRequest,
        analysis: CorrectionAnalysis,
        fixed_code: str,
        lint_output: str | None = None,
    ) -> ReviewVerdict:
        """Review the generated fix and return a verdict (accept / revise / reject)."""

    @abstractmethod
    def suggest_tests(
        self,
        request: AnalyzeRequest,
        analysis: CorrectionAnalysis,
    ) -> TestSuiteOutput:
        """Generate a targeted test suite for the corrected code."""
