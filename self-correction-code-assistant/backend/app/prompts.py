"""Prompt templates for the LLM-based correction loop."""

SYSTEM_PROMPT = """You are an expert code debugging assistant. You analyze broken code, identify bugs, and produce minimal targeted fixes.

Rules:
- Never execute code. Only reason about it.
- Return structured JSON as specified in the user prompt.
- Confidence score must be between 0.0 and 1.0.
- Keep fixes minimal. Do not refactor unrelated code.
- Explain reasoning clearly in 1-3 sentences."""


ANALYZE_PROMPT = """Analyze the following broken code and return a JSON object with these exact keys:
- bug_summary: one-sentence summary of the bug
- root_cause: specific technical root cause
- fix_strategy: what the fix should do
- risks: array of 1-3 potential risks with the fix
- fixed_code: the corrected source code
- explanation: 1-3 sentence explanation of the fix
- confidence_score: float 0.0-1.0 how confident you are
- suggested_tests: array of 2-4 test suggestions

Language: {language}
Error message: {error_message}
Context: {user_context}

Code:
```
{code}
```

Respond ONLY with valid JSON. No markdown fencing, no extra text."""


SELF_CORRECT_PROMPT = """You previously attempted to fix code but the fix did not fully resolve the issue. Using the validation feedback below, produce an improved fix.

Language: {language}
Original code:
```
{original_code}
```

Your previous fix (attempt {attempt_number}):
```
{previous_fixed_code}
```

Validation feedback / test output:
{feedback}

Previous attempts history:
{attempts_history}

Return a JSON object with these exact keys:
- bug_summary: updated one-sentence summary
- root_cause: updated root cause given new evidence
- fix_strategy: what this new fix changes
- risks: array of 1-3 risks
- fixed_code: the improved corrected source code
- explanation: 1-3 sentence explanation of the improvement
- confidence_score: float 0.0-1.0
- suggested_tests: array of 2-4 test suggestions

Respond ONLY with valid JSON. No markdown fencing, no extra text."""


SUMMARIZE_CHANGE_PROMPT = """Compare these two code versions and describe what changed in one sentence.

Previous version:
```
{previous_code}
```

New version:
```
{new_code}
```

Return ONLY a single sentence describing the change. No JSON, no markdown."""


REVIEW_PROMPT = """You are a senior code reviewer. A bug-fix has been generated. Review it and return a structured verdict.

Language: {language}
Original error: {error_message}
Bug summary: {bug_summary}
Fix strategy: {fix_strategy}

Original code:
```
{original_code}
```

Proposed fix:
```
{fixed_code}
```

Static lint output (empty means no issues found):
{lint_output}

Return a JSON object with these exact keys:
- passed: boolean — true if the fix is acceptable
- issues: array of strings — specific problems found (empty if passed)
- reviewer_confidence: float 0.0-1.0
- recommendation: one of "accept", "revise", "reject"

Rules:
- Reject if the fix introduces a syntax error or ignores the reported error.
- Revise if the fix is correct but incomplete or lint issues exist.
- Accept if the fix addresses the root cause with no new issues.

Respond ONLY with valid JSON. No markdown fencing, no extra text."""


TEST_SUGGEST_PROMPT = """You are a test engineer. Given the bug and its fix, generate a targeted test suite.

Language: {language}
Bug summary: {bug_summary}
Root cause: {root_cause}
Fix strategy: {fix_strategy}

Fixed code:
```
{fixed_code}
```

Return a JSON object with these exact keys:
- tests: array of 3-5 specific test case descriptions (not code, just descriptions)
- test_strategy: one sentence describing the overall testing approach
- coverage_notes: one sentence on what edge cases or paths to prioritize

Respond ONLY with valid JSON. No markdown fencing, no extra text."""
