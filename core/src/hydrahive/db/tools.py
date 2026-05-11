from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


@dataclass
class ToolCall:
    id: str
    message_id: str
    tool_name: str
    arguments: dict
    status: str = "pending"
    result: Any = None
    duration_ms: int | None = None
    created_at: str = ""
    metadata: dict = field(default_factory=dict)
    # Token-Audit #129
    session_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    tool_use_id: str | None = None
    iteration: int | None = None
    arguments_size_bytes: int | None = None
    result_size_bytes: int | None = None
    result_truncated: bool | None = None
    truncate_limit_chars: int | None = None
    error_type: str | None = None
    error_message: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ToolCall":
        result: Any = None
        if row["result"]:
            try:
                result = json.loads(row["result"])
            except json.JSONDecodeError:
                result = row["result"]
        cols = row.keys()
        def _get(name: str) -> Any:
            return row[name] if name in cols else None
        rt = _get("result_truncated")
        return cls(
            id=row["id"],
            message_id=row["message_id"],
            tool_name=row["tool_name"],
            arguments=json.loads(row["arguments"]),
            status=row["status"],
            result=result,
            duration_ms=row["duration_ms"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            session_id=_get("session_id"),
            agent_id=_get("agent_id"),
            user_id=_get("user_id"),
            tool_use_id=_get("tool_use_id"),
            iteration=_get("iteration"),
            arguments_size_bytes=_get("arguments_size_bytes"),
            result_size_bytes=_get("result_size_bytes"),
            result_truncated=None if rt is None else bool(rt),
            truncate_limit_chars=_get("truncate_limit_chars"),
            error_type=_get("error_type"),
            error_message=_get("error_message"),
        )


def create(
    message_id: str,
    tool_name: str,
    arguments: dict,
    metadata: dict | None = None,
    *,
    session_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    tool_use_id: str | None = None,
    iteration: int | None = None,
) -> ToolCall:
    arg_blob = json.dumps(arguments)
    tc = ToolCall(
        id=uuid7(),
        message_id=message_id,
        tool_name=tool_name,
        arguments=arguments,
        status="pending",
        created_at=now_iso(),
        metadata=metadata or {},
        session_id=session_id,
        agent_id=agent_id,
        user_id=user_id,
        tool_use_id=tool_use_id,
        iteration=iteration,
        arguments_size_bytes=len(arg_blob),
    )
    with db() as conn:
        conn.execute(
            """INSERT INTO tool_calls
               (id, message_id, tool_name, arguments, status, created_at, metadata,
                session_id, agent_id, user_id, tool_use_id, iteration, arguments_size_bytes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tc.id, tc.message_id, tc.tool_name,
                arg_blob, tc.status, tc.created_at,
                json.dumps(tc.metadata) if tc.metadata else None,
                tc.session_id, tc.agent_id, tc.user_id,
                tc.tool_use_id, tc.iteration, tc.arguments_size_bytes,
            ),
        )
    return tc


def finish(
    tool_call_id: str,
    result: Any,
    status: str = "success",
    duration_ms: int | None = None,
    *,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    result_str = result if isinstance(result, str) else json.dumps(result)
    result_size = len(result_str) if result_str else 0
    with db() as conn:
        conn.execute(
            """UPDATE tool_calls
               SET result = ?, status = ?, duration_ms = ?,
                   result_size_bytes = ?, error_type = ?, error_message = ?
               WHERE id = ?""",
            (result_str, status, duration_ms, result_size, error_type, error_message, tool_call_id),
        )


def mark_truncated(tool_call_id: str, limit_chars: int) -> None:
    """Markiert eine tool_call-Zeile als 'Output abgeschnitten' (Token-Audit #129)."""
    with db() as conn:
        conn.execute(
            "UPDATE tool_calls SET result_truncated = 1, truncate_limit_chars = ? WHERE id = ?",
            (limit_chars, tool_call_id),
        )


def get(tool_call_id: str) -> ToolCall | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM tool_calls WHERE id = ?", (tool_call_id,)).fetchone()
    return ToolCall.from_row(row) if row else None


def list_for_message(message_id: str) -> list[ToolCall]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM tool_calls WHERE message_id = ? ORDER BY created_at ASC",
            (message_id,),
        ).fetchall()
    return [ToolCall.from_row(r) for r in rows]


def list_for_session(session_id: str) -> list[ToolCall]:
    """Token-Audit #129: alle tool_calls einer Session direkt — ohne JOIN über messages."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [ToolCall.from_row(r) for r in rows]
