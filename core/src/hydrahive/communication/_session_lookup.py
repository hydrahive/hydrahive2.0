"""Find-or-create für Channel-Sessions.

Pro (master_agent, channel, external_user_id) genau eine persistente Session
damit der Master-Agent den Gesprächsverlauf eines Senders behält.
"""
from __future__ import annotations

from hydrahive.db import sessions as sessions_db
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def find_or_create(
    *,
    agent_id: str,
    user_id: str,
    channel: str,
    external_user_id: str,
    title_hint: str | None = None,
) -> sessions_db.Session:
    """Existierende Channel-Session zurück oder lege eine neue an."""
    with db() as conn:
        row = conn.execute(
            """SELECT * FROM sessions
                WHERE agent_id = ? AND channel = ? AND external_user_id = ?
                ORDER BY updated_at DESC LIMIT 1""",
            (agent_id, channel, external_user_id),
        ).fetchone()
        if row:
            return sessions_db.Session.from_row(row)

        sid = uuid7()
        ts = now_iso()
        title = title_hint or f"{channel}:{external_user_id}"
        conn.execute(
            """INSERT INTO sessions
                (id, agent_id, project_id, user_id, title, created_at, updated_at, status,
                 metadata, channel, external_user_id)
                VALUES (?, ?, NULL, ?, ?, ?, ?, 'active', NULL, ?, ?)""",
            (sid, agent_id, user_id, title, ts, ts, channel, external_user_id),
        )
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    return sessions_db.Session.from_row(row)
