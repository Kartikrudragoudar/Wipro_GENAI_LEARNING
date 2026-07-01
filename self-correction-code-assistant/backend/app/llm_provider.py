"""LLM-based AI provider using LangChain with support for OpenAI, Google Gemini, and Anthropic Claude."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.ai_provider import AIProvider
from app.models import AnalyzeRequest, CorrectionAnalysis, ReviewVerdict, SelfCorrectRequest, TestSuiteOutput
from app.prompts import (
    ANALYZE_PROMPT,
    REVIEW_PROMPT,
    SELF_CORRECT_PROMPT,
    SUMMARIZE_CHANGE_PROMPT,
    SYSTEM_PROMPT,
    TEST_SUGGEST_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMProvider(AIProvider):
    """Real LLM-backed provider. Works with any LangChain chat model."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def _invoke(self, user_prompt: str) -> str:
        """Send system + user message and return the text response."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = self.llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from LLM response, stripping markdown fences if present."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)

    def analyze_code(self, request: AnalyzeRequest) -> CorrectionAnalysis:
        prompt = ANALYZE_PROMPT.format(
            language=request.language,
            error_message=request.error_message,
            user_context=request.user_context or "No additional context provided.",
            code=request.code,
        )
        raw = self._invoke(prompt)
        data = self._parse_json(raw)
        # Store extra fields for generate_fix to pick up
        self._last_analysis_data = data
        return CorrectionAnalysis(
            bug_summary=data["bug_summary"],
            root_cause=data["root_cause"],
            fix_strategy=data["fix_strategy"],
            risks=data.get("risks", []),
        )

    def generate_fix(self, request: AnalyzeRequest, analysis: CorrectionAnalysis) -> tuple[str, str, float, list[str]]:
        # The analyze step already produced the full response including the fix
        data = getattr(self, "_last_analysis_data", None)
        if data and "fixed_code" in data:
            return (
                data["fixed_code"],
                data["explanation"],
                float(data.get("confidence_score", 0.75)),
                data.get("suggested_tests", []),
            )
        # Fallback: re-invoke if data was lost
        prompt = ANALYZE_PROMPT.format(
            language=request.language,
            error_message=request.error_message,
            user_context=request.user_context or "No additional context provided.",
            code=request.code,
        )
        raw = self._invoke(prompt)
        data = self._parse_json(raw)
        return (
            data["fixed_code"],
            data["explanation"],
            float(data.get("confidence_score", 0.75)),
            data.get("suggested_tests", []),
        )

    def self_correct(self, request: SelfCorrectRequest) -> tuple[CorrectionAnalysis, str, str, float, list[str]]:
        feedback = f"{request.test_output or ''}\n{request.user_feedback or ''}".strip()
        attempts_history = ""
        for attempt in request.previous_attempts:
            attempts_history += f"\n--- Attempt {attempt.attempt_number} ({attempt.status}) ---\n"
            attempts_history += f"Summary: {attempt.bug_summary}\n"
            attempts_history += f"Change: {attempt.change_summary}\n"

        prompt = SELF_CORRECT_PROMPT.format(
            language=request.language,
            original_code=request.original_code,
            attempt_number=request.attempt_number,
            previous_fixed_code=request.previous_fixed_code,
            feedback=feedback or "No specific feedback provided.",
            attempts_history=attempts_history or "No previous attempts.",
        )
        raw = self._invoke(prompt)
        data = self._parse_json(raw)

        analysis = CorrectionAnalysis(
            bug_summary=data["bug_summary"],
            root_cause=data["root_cause"],
            fix_strategy=data["fix_strategy"],
            risks=data.get("risks", []),
        )
        return (
            analysis,
            data["fixed_code"],
            data["explanation"],
            float(data.get("confidence_score", 0.75)),
            data.get("suggested_tests", []),
        )

    def summarize_attempt_change(self, previous_code: str, new_code: str) -> str:
        if previous_code == new_code:
            return "No source change was needed; the attempt updates the reasoning and validation guidance."
        prompt = SUMMARIZE_CHANGE_PROMPT.format(
            previous_code=previous_code,
            new_code=new_code,
        )
        return self._invoke(prompt).strip()

    def review_fix(
        self,
        request: AnalyzeRequest,
        analysis: CorrectionAnalysis,
        fixed_code: str,
        lint_output: str | None = None,
    ) -> ReviewVerdict:
        prompt = REVIEW_PROMPT.format(
            language=request.language,
            error_message=request.error_message,
            bug_summary=analysis.bug_summary,
            fix_strategy=analysis.fix_strategy,
            original_code=request.code,
            fixed_code=fixed_code,
            lint_output=lint_output or "(none)",
        )
        raw = self._invoke(prompt)
        data = self._parse_json(raw)
        return ReviewVerdict(
            passed=bool(data.get("passed", False)),
            issues=data.get("issues", []),
            reviewer_confidence=float(data.get("reviewer_confidence", 0.5)),
            recommendation=data.get("recommendation", "revise"),
            lint_output=lint_output,
        )

    def suggest_tests(
        self,
        request: AnalyzeRequest,
        analysis: CorrectionAnalysis,
    ) -> TestSuiteOutput:
        fixed_code = getattr(self, "_last_analysis_data", {}).get("fixed_code", "")
        prompt = TEST_SUGGEST_PROMPT.format(
            language=request.language,
            bug_summary=analysis.bug_summary,
            root_cause=analysis.root_cause,
            fix_strategy=analysis.fix_strategy,
            fixed_code=fixed_code or "(not available)",
        )
        raw = self._invoke(prompt)
        data = self._parse_json(raw)
        return TestSuiteOutput(
            tests=data.get("tests", []),
            test_strategy=data.get("test_strategy", ""),
            coverage_notes=data.get("coverage_notes", ""),
        )
