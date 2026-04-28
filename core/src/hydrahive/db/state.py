from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

_SENTINEL = object()


def set(
    session_id: str,
    key: str,
    value: Any,
    metadata: dict | None = None,
) -> None:
    """Upsert a key/value pair in session_state. Value is JSON-serialized."""
    with db() as conn:
        conn.execute(
            """INSERT INTO session_state (session_id, key, value, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (session_id, key) DO UPDATE SET
                 value      = excluded.value,
                 updated_at = excluded.updated_at,
                 metadata   = excluded.metadata""",
            (
                session_id, key, json.dumps(value), now_iso(),
                json.dumps(metadata) if metadata else None,
            ),
        )


def get(session_id: str, key: str, default: Any = None) -> Any:
    with db() as conn:
        row = conn.execute(
            "SELECT value FROM session_state WHERE session_id = ? AND key = ?",
            (session_id, key),
        ).fetchone()
    if not row:
        return default
    return json.loads(row["value"])


def delete(session_id: str, key: str) -> None:
    with db() as conn:
        conn.execute(
            "DELETE FROM session_state WHERE session_id = ? AND key = ?",
            (session_id, key),
        )


def list_keys(session_id: str, prefix: str = "") -> list[str]:
    with db() as conn:
        if prefix:
            rows = conn.execute(
                "SELECT key FROM session_state WHERE session_id = ? AND key LIKE ? ORDER BY key",
                (session_id, prefix + "%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key FROM session_state WHERE session_id = ? ORDER BY key",
                (session_id,),
            ).fetchall()
    return [r["key"] for r in rows]
