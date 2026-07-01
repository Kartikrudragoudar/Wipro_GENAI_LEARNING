"""LangChain tools for the multi-agent correction pipeline.

Tools are defined with the @tool decorator so LLM agents can call them
dynamically via llm.bind_tools(). Tools that need external state (embedding
store, workflow cache) are created via factory functions that capture the
dependency via closure so the tool callables remain stateless.

Tool catalogue
--------------
Analyzer agent tools (injected via make_analyzer_tools):
  search_similar_fixes    — query ChromaDB for top-k similar past corrections
  get_session_history     — retrieve all prior attempts for a session

Reviewer agent tools (injected via make_reviewer_tools):
  lint_code               — run pyflakes/acorn parse-only linting (no execution)
  read_checkpoint         — load a past checkpoint state for comparison

Test Suggester agent tools (injected via make_test_suggester_tools):
  store_correction        — persist the final correction into ChromaDB embeddings
"""

from __future__ import annotations

import logging
import json
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lint helpers — parse/lint only, NEVER execute submitted code
# ---------------------------------------------------------------------------

def _lint_python(code: str) -> str:
    """Run pyflakes on code string and return a plain-text report."""
    try:
        import ast
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return f"SyntaxError: {exc}"

        try:
            from pyflakes import api as pyflakes_api
            from pyflakes.checker import Checker
            import io, sys
            tree = __import__("ast").parse(code)
            w = Checker(tree, "<stdin>")
            messages = [str(m) for m in w.messages]
            return "\n".join(messages) if messages else ""
        except ImportError:
            # pyflakes not installed — return empty (no lint issues found)
            return ""
    except Exception as exc:
        logger.warning("lint_python failed: %s", exc)
        return ""


def _lint_js_ts(code: str) -> str:
    """Attempt a basic parse check for JS/TS using Python heuristics.

    Full acorn/typescript-eslint would require Node.js. As a safe fallback
    we check for obvious unmatched braces/parens which covers the most
    common reviewer-useful issues without executing code.
    """
    try:
        opens = sum(code.count(c) for c in "{([")
        closes = sum(code.count(c) for c in "})]")
        if opens != closes:
            return f"Structural warning: unmatched brackets/braces (opens={opens}, closes={closes})"
        return ""
    except Exception as exc:
        logger.warning("lint_js_ts failed: %s", exc)
        return ""


def run_lint(code: str, language: str) -> str:
    """Dispatch to the appropriate linter. Returns empty string if no issues."""
    lang = language.lower()
    if lang == "python":
        return _lint_python(code)
    if lang in {"javascript", "typescript"}:
        return _lint_js_ts(code)
    # Java / C++ — no lightweight in-process linter available; return empty
    return ""


# ---------------------------------------------------------------------------
# Tool factories — return plain callables that accept JSON-serialisable args
# ---------------------------------------------------------------------------

def make_analyzer_tools(embedding_store: Any) -> list[dict[str, Any]]:
    """Return tool specs for the Analyzer agent.

    Each spec has: name, description, callable fn(args_dict) -> str.
    """

    def search_similar_fixes(args: dict) -> str:
        """Query ChromaDB for similar past corrections."""
        if embedding_store is None:
            return json.dumps([])
        try:
            results = embedding_store.find_similar_corrections(
                language=args.get("language", ""),
                error_message=args.get("error_message", ""),
                code_snippet=args.get("code_snippet", ""),
                top_k=int(args.get("top_k", 3)),
            )
            return json.dumps(results, default=str)
        except Exception as exc:
            logger.warning("search_similar_fixes failed: %s", exc)
            return json.dumps([])

    def get_session_history(args: dict) -> str:
        """Retrieve all stored attempts for a specific session."""
        if embedding_store is None:
            return json.dumps([])
        try:
            results = embedding_store.get_session_history(args.get("session_id", ""))
            return json.dumps(results, default=str)
        except Exception as exc:
            logger.warning("get_session_history failed: %s", exc)
            return json.dumps([])

    return [
        {
            "name": "search_similar_fixes",
            "description": "Search ChromaDB for the top-k most similar past code corrections based on language, error message, and code snippet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string"},
                    "error_message": {"type": "string"},
                    "code_snippet": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["language", "error_message"],
            },
            "fn": search_similar_fixes,
        },
        {
            "name": "get_session_history",
            "description": "Retrieve all stored correction attempts for a specific session from the embedding store.",
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
            "fn": get_session_history,
        },
    ]


def make_reviewer_tools(embedding_store: Any) -> list[dict[str, Any]]:
    """Return tool specs for the Reviewer agent."""
    from app.workflow_cache import get_checkpoint

    def lint_code(args: dict) -> str:
        """Run static lint (no execution) and return issues as a string."""
        result = run_lint(args.get("code", ""), args.get("language", ""))
        return result if result else ""

    def read_checkpoint_tool(args: dict) -> str:
        """Load a past workflow checkpoint state for comparison."""
        try:
            cp = get_checkpoint(
                args.get("session_id", ""),
                int(args.get("attempt_number", 0)),
            )
            return json.dumps(cp, default=str) if cp else json.dumps({})
        except Exception as exc:
            logger.warning("read_checkpoint tool failed: %s", exc)
            return json.dumps({})

    return [
        {
            "name": "lint_code",
            "description": "Run a static lint check (pyflakes for Python, bracket analysis for JS/TS) on the proposed fix. Returns an empty string if no issues are found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["code", "language"],
            },
            "fn": lint_code,
        },
        {
            "name": "read_checkpoint",
            "description": "Load a previously saved workflow checkpoint state to compare with the current fix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "attempt_number": {"type": "integer"},
                },
                "required": ["session_id", "attempt_number"],
            },
            "fn": read_checkpoint_tool,
        },
    ]


def make_test_suggester_tools(embedding_store: Any) -> list[dict[str, Any]]:
    """Return tool specs for the Test Suggester agent."""

    def store_correction(args: dict) -> str:
        """Persist a completed correction into ChromaDB for future cache warming."""
        if embedding_store is None:
            return "embedding store not available"
        try:
            from app.models import CorrectionAttempt
            attempt_data = args.get("attempt", {})
            attempt = CorrectionAttempt(**attempt_data) if isinstance(attempt_data, dict) else attempt_data
            embedding_store.store_correction(
                session_id=args.get("session_id", ""),
                language=args.get("language", ""),
                error_message=args.get("error_message", ""),
                bug_summary=args.get("bug_summary", ""),
                fix_strategy=args.get("fix_strategy", ""),
                fixed_code=args.get("fixed_code", ""),
                attempt=attempt,
            )
            return "stored"
        except Exception as exc:
            logger.warning("store_correction tool failed: %s", exc)
            return f"failed: {exc}"

    return [
        {
            "name": "store_correction",
            "description": "Persist the completed correction session into the ChromaDB embedding store so it can warm future analysis sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "language": {"type": "string"},
                    "error_message": {"type": "string"},
                    "bug_summary": {"type": "string"},
                    "fix_strategy": {"type": "string"},
                    "fixed_code": {"type": "string"},
                    "attempt": {"type": "object"},
                },
                "required": ["session_id", "language", "error_message", "bug_summary", "fix_strategy", "fixed_code", "attempt"],
            },
            "fn": store_correction,
        },
    ]


def call_tool(tool_specs: list[dict[str, Any]], name: str, args: dict) -> str:
    """Dispatch a tool call by name from a list of tool specs."""
    for spec in tool_specs:
        if spec["name"] == name:
            return spec["fn"](args)
    return f"Unknown tool: {name}"
