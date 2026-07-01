"""Workflow state cache — stores and retrieves LangGraph agent workflow states.

Features:
1. TTL expiration — stale sessions auto-expire after a configurable duration
2. Checkpoint snapshots — each attempt is stored separately for rollback/branching
3. SQLite persistence — states survive server restarts
4. LRU eviction — oldest sessions evicted when max size is reached
"""

import json
import os
import logging
import sqlite3
import time
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_max_size = int(os.getenv("WORKFLOW_CACHE_MAX_SIZE", "100"))
_ttl_seconds = int(os.getenv("WORKFLOW_CACHE_TTL", "3600"))
_db_path = os.getenv(
    "WORKFLOW_CACHE_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow_cache.db"),
)


class _SQLiteStateStore:
    """LRU + TTL key-value store backed by SQLite with checkpoint snapshots."""

    def __init__(self, db_path: str, maxsize: int, ttl: int):
        self._db_path = db_path
        self._maxsize = maxsize
        self._ttl = ttl
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_states (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(session_id, attempt_number)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cp_session ON checkpoints(session_id)"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def _purge_expired(self, conn: sqlite3.Connection) -> None:
        cutoff = time.time() - self._ttl
        conn.execute("DELETE FROM workflow_states WHERE updated_at < ?", (cutoff,))
        conn.execute("DELETE FROM checkpoints WHERE created_at < ?", (cutoff,))

    def _enforce_max_size(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM workflow_states").fetchone()[0]
        if count > self._maxsize:
            excess = count - self._maxsize
            conn.execute("""
                DELETE FROM workflow_states WHERE session_id IN (
                    SELECT session_id FROM workflow_states
                    ORDER BY updated_at ASC LIMIT ?
                )
            """, (excess,))
            logger.debug("Evicted %d oldest sessions from workflow cache", excess)

    # --- Main state ---

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            self._purge_expired(conn)
            row = conn.execute(
                "SELECT state_json FROM workflow_states WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE workflow_states SET updated_at = ? WHERE session_id = ?",
                (time.time(), session_id),
            )
            conn.commit()
            return json.loads(row[0])

    def set(self, session_id: str, state: dict[str, Any]) -> None:
        now = time.time()
        state_json = json.dumps(state, default=str)
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO workflow_states (session_id, state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id)
                DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
            """, (session_id, state_json, now, now))
            self._enforce_max_size(conn)
            conn.commit()

    def delete(self, session_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM workflow_states WHERE session_id = ?", (session_id,)
            )
            conn.execute(
                "DELETE FROM checkpoints WHERE session_id = ?", (session_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    # --- Checkpoint snapshots ---

    def save_checkpoint(
        self, session_id: str, attempt_number: int, state: dict[str, Any]
    ) -> None:
        now = time.time()
        cp_id = f"{session_id}:attempt:{attempt_number}"
        state_json = json.dumps(state, default=str)
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO checkpoints (id, session_id, attempt_number, state_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id, attempt_number)
                DO UPDATE SET state_json = excluded.state_json, created_at = excluded.created_at
            """, (cp_id, session_id, attempt_number, state_json, now))
            conn.commit()
        logger.info(
            "Checkpoint saved: session=%s attempt=%d", session_id, attempt_number
        )

    def get_checkpoint(
        self, session_id: str, attempt_number: int
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM checkpoints "
                "WHERE session_id = ? AND attempt_number = ?",
                (session_id, attempt_number),
            ).fetchone()
            return json.loads(row[0]) if row else None

    def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT attempt_number, created_at FROM checkpoints "
                "WHERE session_id = ? ORDER BY attempt_number",
                (session_id,),
            ).fetchall()
            return [{"attempt_number": r[0], "created_at": r[1]} for r in rows]

    # --- Stats ---

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM workflow_states").fetchone()[0]

    def checkpoint_count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]

    def db_size_kb(self) -> int:
        try:
            return os.path.getsize(self._db_path) // 1024
        except OSError:
            return 0


@lru_cache(maxsize=1)
def _get_store() -> _SQLiteStateStore:
    """Singleton SQLite state store (cached via lru_cache)."""
    return _SQLiteStateStore(db_path=_db_path, maxsize=_max_size, ttl=_ttl_seconds)


# --- Public API ---


def save_workflow_state(session_id: str, state: dict[str, Any]) -> None:
    """Persist workflow state for a session."""
    _get_store().set(session_id, state)
    logger.info("Saved workflow state for session %s", session_id)


def get_workflow_state(session_id: str) -> dict[str, Any] | None:
    """Retrieve cached workflow state. Returns None if expired/evicted/not found."""
    return _get_store().get(session_id)


def delete_workflow_state(session_id: str) -> bool:
    """Remove a session's workflow state and checkpoints."""
    return _get_store().delete(session_id)


def save_checkpoint(
    session_id: str, attempt_number: int, state: dict[str, Any]
) -> None:
    """Save a checkpoint snapshot at a specific attempt number."""
    _get_store().save_checkpoint(session_id, attempt_number, state)


def get_checkpoint(session_id: str, attempt_number: int) -> dict[str, Any] | None:
    """Retrieve a checkpoint snapshot for rollback/branching."""
    return _get_store().get_checkpoint(session_id, attempt_number)


def list_checkpoints(session_id: str) -> list[dict[str, Any]]:
    """List all checkpoints for a session."""
    return _get_store().list_checkpoints(session_id)


def get_cache_stats() -> dict[str, Any]:
    """Return cache utilization info."""
    store = _get_store()
    return {
        "active_sessions": store.count(),
        "total_checkpoints": store.checkpoint_count(),
        "max_size": _max_size,
        "ttl_seconds": _ttl_seconds,
        "db_size_kb": store.db_size_kb(),
    }