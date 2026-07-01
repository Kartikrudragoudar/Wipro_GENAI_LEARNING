from app.ai_provider import AIProvider
from app.models import AnalyzeRequest, CorrectionAnalysis, ReviewVerdict, SelfCorrectRequest, TestSuiteOutput


class MockAIProvider(AIProvider):
    def analyze_code(self, request: AnalyzeRequest) -> CorrectionAnalysis:
        code_lower = request.code.lower()
        error_lower = request.error_message.lower()

        if request.language == "Python" and ("nameerror" in error_lower or "pritn" in code_lower):
            return CorrectionAnalysis(
                bug_summary="Python name resolution failure caused by a typo or undefined symbol.",
                root_cause="The code references a name that does not exist in the current scope, often because of a misspelled function or variable.",
                fix_strategy="Normalize the misspelled identifier and keep the surrounding control flow unchanged.",
                risks=["A similarly named variable may have been intended instead", "The fix should be checked with the exact runtime input"],
            )

        if request.language == "JavaScript" and ("undefined" in error_lower or "not defined" in error_lower):
            return CorrectionAnalysis(
                bug_summary="JavaScript code reads a value before it is declared or passed in.",
                root_cause="A variable is referenced without a local declaration, import, parameter, or safe fallback.",
                fix_strategy="Introduce the missing variable in the narrowest scope and preserve existing behavior.",
                risks=["The missing value may need to come from API data", "A fallback can hide upstream data issues"],
            )

        if request.language == "TypeScript" and ("type" in error_lower or "assignable" in error_lower):
            return CorrectionAnalysis(
                bug_summary="TypeScript type mismatch between the assigned value and the expected shape.",
                root_cause="The implementation returns or assigns a value that does not satisfy the declared type contract.",
                fix_strategy="Align the implementation with the declared type while avoiding unsafe casts.",
                risks=["Over-broad types can weaken safety", "Runtime data should still be validated"],
            )

        if "import" in error_lower or "module" in error_lower or "cannot find" in error_lower:
            return CorrectionAnalysis(
                bug_summary="Missing import or unresolved module dependency.",
                root_cause="The code uses a symbol or module that is not imported, exported, or available in the runtime path.",
                fix_strategy="Add the missing import or replace the reference with a locally available symbol.",
                risks=["Import paths can differ by project structure", "The package may still need to be installed"],
            )

        return CorrectionAnalysis(
            bug_summary="Likely logic bug causing output to diverge from the expected behavior.",
            root_cause="The implementation appears structurally valid but contains an incorrect condition, accumulator, or return value.",
            fix_strategy="Apply a minimal logic correction and suggest targeted tests for the failing path.",
            risks=["The provided error may not cover all edge cases", "A broader test case could reveal a second issue"],
        )

    def generate_fix(self, request: AnalyzeRequest, analysis: CorrectionAnalysis) -> tuple[str, str, float, list[str]]:
        fixed_code = self._apply_basic_fix(request.code, request.language, request.error_message)
        explanation = f"Applied the first correction strategy: {analysis.fix_strategy} The change is intentionally small so it can be validated with pasted test output."
        tests = self._suggest_tests(request.language)
        confidence = 0.78 if fixed_code != request.code else 0.58
        return fixed_code, explanation, confidence, tests

    def self_correct(self, request: SelfCorrectRequest) -> tuple[CorrectionAnalysis, str, str, float, list[str]]:
        feedback = f"{request.test_output or ''} {request.user_feedback or ''}".lower()
        analysis = CorrectionAnalysis(
            bug_summary="Previous correction needs refinement based on validation feedback.",
            root_cause="The pasted feedback indicates the first fix did not fully address the failing behavior or missed an adjacent condition.",
            fix_strategy="Preserve the working parts of the previous fix, then address the new failure signal from validation feedback.",
            risks=["The feedback may describe a different failing path", "Manual validation is still required because code execution is disabled in this MVP"],
        )
        improved_code = request.previous_fixed_code

        if "import" in feedback and request.language in {"JavaScript", "TypeScript"}:
            improved_code = "import React from 'react';\n" + improved_code if "react" in feedback and "import React" not in improved_code else improved_code
        elif "none" in feedback and request.language == "Python":
            improved_code = improved_code.replace("return result", "return result if result is not None else 0")
        elif "undefined" in feedback and request.language in {"JavaScript", "TypeScript"}:
            improved_code = improved_code.replace("const result =", "const result = typeof input !== 'undefined' ?")
        else:
            improved_code = self._append_review_note(improved_code, request.language)

        explanation = "Used validation feedback to produce a second correction attempt. The backend did not execute the code; it treated the pasted output as the validation signal."
        confidence = min(0.92, 0.64 + (request.attempt_number * 0.08))
        return analysis, improved_code, explanation, confidence, self._suggest_tests(request.language)

    def summarize_attempt_change(self, previous_code: str, new_code: str) -> str:
        if previous_code == new_code:
            return "No source change was needed; the attempt updates the reasoning and validation guidance."
        previous_lines = previous_code.splitlines()
        new_lines = new_code.splitlines()
        return f"Updated the fix from {len(previous_lines)} to {len(new_lines)} lines and adjusted the implementation based on the latest feedback."

    def review_fix(
        self,
        request: AnalyzeRequest,
        analysis: CorrectionAnalysis,
        fixed_code: str,
        lint_output: str | None = None,
    ) -> ReviewVerdict:
        has_lint_issues = bool(lint_output and lint_output.strip())
        # Heuristic: if the fix looks unchanged or has lint errors, revise
        if fixed_code == request.code:
            return ReviewVerdict(
                passed=False,
                issues=["Fix is identical to the original code — no change was applied."],
                reviewer_confidence=0.3,
                recommendation="revise",
                lint_output=lint_output,
            )
        if has_lint_issues:
            return ReviewVerdict(
                passed=False,
                issues=[f"Static analysis found issues: {lint_output}"],
                reviewer_confidence=0.45,
                recommendation="revise",
                lint_output=lint_output,
            )
        return ReviewVerdict(
            passed=True,
            issues=[],
            reviewer_confidence=0.82,
            recommendation="accept",
            lint_output=lint_output,
        )

    def suggest_tests(
        self,
        request: AnalyzeRequest,
        analysis: CorrectionAnalysis,
    ) -> TestSuiteOutput:
        tests = self._suggest_tests(request.language)
        return TestSuiteOutput(
            tests=tests,
            test_strategy=f"Unit-test the specific bug path: {analysis.fix_strategy[:80]}",
            coverage_notes="Focus on the error path, a happy path, and one boundary/edge case.",
        )

    def _apply_basic_fix(self, code: str, language: str, error_message: str) -> str:
        error_lower = error_message.lower()
        fixed = code

        if language == "Python":
            fixed = fixed.replace("pritn(", "print(").replace("lenght", "length")
            if "nameerror" in error_lower and "total" in error_lower and "total =" not in fixed:
                fixed = "total = 0\n" + fixed
        elif language == "JavaScript":
            fixed = fixed.replace("consol.log", "console.log")
            if "user" in error_lower and "const user" not in fixed:
                fixed = "const user = { name: 'Developer' };\n" + fixed
        elif language == "TypeScript":
            fixed = fixed.replace(": string = 0", ": number = 0").replace(": number = ''", ": string = ''")
            fixed = fixed.replace("as any", "")
        elif language == "Java":
            fixed = fixed.replace("System.out.prinln", "System.out.println")
        elif language == "C++":
            if "#include" not in fixed and "cout" in fixed:
                fixed = "#include <iostream>\nusing namespace std;\n" + fixed
            fixed = fixed.replace("retrun", "return")

        if fixed == code:
            return self._append_review_note(code, language)
        return fixed

    def _append_review_note(self, code: str, language: str) -> str:
        comment = {
            "Python": "# Review: adjusted after loop feedback; verify edge cases.",
            "JavaScript": "// Review: adjusted after loop feedback; verify edge cases.",
            "TypeScript": "// Review: adjusted after loop feedback; verify edge cases.",
            "Java": "// Review: adjusted after loop feedback; verify edge cases.",
            "C++": "// Review: adjusted after loop feedback; verify edge cases.",
        }.get(language, "// Review: adjusted after loop feedback; verify edge cases.")
        return f"{code.rstrip()}\n{comment}\n"

    def _suggest_tests(self, language: str) -> list[str]:
        if language == "Python":
            return ["Run the failing script again", "Add a pytest case for the reported input", "Check an empty or missing-value edge case"]
        if language in {"JavaScript", "TypeScript"}:
            return ["Run npm test or the failing command", "Add a unit test for the undefined or typed value", "Check browser or Node console output"]
        if language == "Java":
            return ["Run javac on the changed file", "Add a JUnit test for the failing branch", "Check null and boundary inputs"]
        return ["Compile the file", "Run the failing input again", "Add a boundary-case assertion"]
