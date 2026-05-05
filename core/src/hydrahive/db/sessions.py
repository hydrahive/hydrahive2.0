from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.db import mirror


@dataclass
class Session:
    id: str
    agent_id: str
    user_id: str
    project_id: str | None = None
    title: str | None = None
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Session":
        return cls(
            id=row["id"],
            agent_id=row["agent_id"],
            user_id=row["user_id"],
            project_id=row["project_id"],
            title=row["title"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


def create(
    agent_id: str,
    user_id: str,
    project_id: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> Session:
    s = Session(
        id=uuid7(),
        agent_id=agent_id,
        user_id=user_id,
        project_id=project_id,
        title=title,
        created_at=now_iso(),
        updated_at=now_iso(),
        metadata=metadata or {},
    )
    s.updated_at = s.created_at
    with db() as conn:
        conn.execute(
            """INSERT INTO sessions
               (id, agent_id, project_id, user_id, title, created_at, updated_at, status, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                s.id, s.agent_id, s.project_id, s.user_id, s.title,
                s.created_at, s.updated_at, s.status,
                json.dumps(s.metadata) if s.metadata else None,
            ),
        )
    mirror.schedule_session(s)
    return s


def get(session_id: str) -> Session | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return Session.from_row(row) if row else None


def list_for_user(user_id: str, limit: int = 50) -> list[Session]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [Session.from_row(r) for r in rows]


def list_for_agent(agent_id: str, limit: int = 50) -> list[Session]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE agent_id = ? ORDER BY updated_at DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
    return [Session.from_row(r) for r in rows]


def update(
    session_id: str,
    *,
    title: str | None = None,
    status: str | None = None,
    metadata: dict | None = None,
) -> None:
    fields: list[str] = []
    values: list = []
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if metadata is not None:
        fields.append("metadata = ?")
        values.append(json.dumps(metadata) if metadata else None)
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(now_iso())
    values.append(session_id)
    with db() as conn:
        conn.execute(f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?", values)
    s = get(session_id)
    if s:
        mirror.schedule_session(s)


def set_model_override(session_id: str, model: str | None) -> None:
    """Setzt session.metadata['model_override']. None entfernt den Override.
    Read-modify-write: andere metadata-Felder bleiben erhalten."""
    s = get(session_id)
    if not s:
        return
    md = dict(s.metadata or {})
    if model:
        md["model_override"] = model
    else:
        md.pop("model_override", None)
    update(session_id, metadata=md)


def touch(session_id: str) -> None:
    with db() as conn:
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now_iso(), session_id))


def delete(session_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
