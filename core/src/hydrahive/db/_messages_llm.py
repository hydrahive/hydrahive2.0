"""list_for_llm: resolve message history respecting compaction."""
from __future__ import annotations

import json

from hydrahive.db._message_model import Message
from hydrahive.db.connection import db


def list_for_llm(session_id: str) -> list[Message]:
    """Returns only the kept portion of history (after latest compaction).

    SQL-optimized: two targeted queries instead of loading full history.
    Caller must separately load the summary via get_latest_summary().
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
