from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


@dataclass
class Message:
    id: str
    session_id: str
    role: str
    content: Any
    created_at: str = ""
    token_count: int | None = None
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Message":
        raw = row["content"]
        try:
            content = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            content = raw
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=content,
            created_at=row["created_at"],
            token_count=row["token_count"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


def append(
    session_id: str,
    role: str,
    content: Any,
    token_count: int | None = None,
    metadata: dict | None = None,
) -> Message:
    m = Message(
        id=uuid7(),
        session_id=session_id,
        role=role,
        content=content,
        created_at=now_iso(),
        token_count=token_count,
        metadata=metadata or {},
    )
    content_str = content if isinstance(content, str) else json.dumps(content)
    with db() as conn:
        conn.execute(
            """INSERT INTO messages
               (id, session_id, role, content, created_at, token_count, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                m.id, m.session_id, m.role, content_str, m.created_at,
                m.token_count,
                json.dumps(m.metadata) if m.metadata else None,
            ),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (m.created_at, session_id),
        )
    return m


def get(message_id: str) -> Message | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return Message.from_row(row) if row else None


def list_for_session(session_id: str, limit: int | None = None) -> list[Message]:
    sql = "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC"
    params: list = [session_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Message.from_row(r) for r in rows]


def list_for_llm(session_id: str) -> list[Message]:
    """Wie list_for_session, aber resolved durch die neueste Compaction.

    Gibt nur die kept-Portion zurück (ab firstKeptEntryId), ohne
    Compaction-Rows. Caller muss `get_latest_summary()` separat laden.

    SQL-optimiert: zwei gezielte Queries statt komplette History-Liste —
    bei großen Sessions massiver Unterschied.
    """
    with db() as conn:
        cmp_row = conn.execute(
            """SELECT id, created_at, metadata FROM messages
               WHERE session_id = ? AND role = 'compaction'
               ORDER BY created_at DESC LIMIT 1""",
            (session_id,),
        ).fetchone()

        if cmp_row is None:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [Message.from_row(r) for r in rows]

        meta = json.loads(cmp_row["metadata"]) if cmp_row["metadata"] else {}
        first_kept = meta.get("firstKeptEntryId")
        if not first_kept:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? AND role != 'compaction' ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [Message.from_row(r) for r in rows]

        ts_row = conn.execute(
            "SELECT created_at FROM messages WHERE id = ?", (first_kept,),
        ).fetchone()
        if not ts_row:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? AND role != 'compaction' ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [Message.from_row(r) for r in rows]

        rows = conn.execute(
            """SELECT * FROM messages
               WHERE session_id = ? AND role != 'compaction' AND created_at >= ?
               ORDER BY created_at ASC""",
            (session_id, ts_row["created_at"]),
        ).fetchall()
    return [Message.from_row(r) for r in rows]


def get_latest_summary(session_id: str) -> str | None:
    """Return the most recent compaction summary text, or None if no compaction yet."""
    with db() as conn:
        row = conn.execute(
            """SELECT content FROM messages
               WHERE session_id = ? AND role = 'compaction'
               ORDER BY created_at DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
    return row["content"] if row else None


def update_tokens(message_id: str, token_count: int) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE messages SET token_count = ? WHERE id = ?",
            (token_count, message_id),
        )


def delete(message_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))


def delete_from(session_id: str, message_id: str) -> int:
    """Löscht die targeted message + alle Folgenden (created_at >=). Wird für
    Edit+Resend genutzt — die alte User-Message wird durch die neue ersetzt."""
    with db() as conn:
        row = conn.execute(
            "SELECT created_at FROM messages WHERE id = ? AND session_id = ?",
            (message_id, session_id),
        ).fetchone()
        if not row:
            return 0
        cur = conn.execute(
            "DELETE FROM messages WHERE session_id = ? AND created_at >= ?",
            (session_id, row["created_at"]),
        )
        return cur.rowcount or 0
