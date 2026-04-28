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

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ToolCall":
        result: Any = None
        if row["result"]:
            try:
                result = json.loads(row["result"])
            except json.JSONDecodeError:
                result = row["result"]
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
        )


def create(
    message_id: str,
    tool_name: str,
    arguments: dict,
    metadata: dict | None = None,
) -> ToolCall:
    tc = ToolCall(
        id=uuid7(),
        message_id=message_id,
        tool_name=tool_name,
        arguments=arguments,
        status="pending",
        created_at=now_iso(),
        metadata=metadata or {},
    )
    with db() as conn:
        conn.execute(
            """INSERT INTO tool_calls
               (id, message_id, tool_name, arguments, status, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                tc.id, tc.message_id, tc.tool_name,
                json.dumps(tc.arguments), tc.status, tc.created_at,
                json.dumps(tc.metadata) if tc.metadata else None,
            ),
        )
    return tc


def finish(
    tool_call_id: str,
    result: Any,
    status: str = "success",
    duration_ms: int | None = None,
) -> None:
    result_str = result if isinstance(result, str) else json.dumps(result)
    with db() as conn:
        conn.execute(
            "UPDATE tool_calls SET result = ?, status = ?, duration_ms = ? WHERE id = ?",
            (result_str, status, duration_ms, tool_call_id),
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
