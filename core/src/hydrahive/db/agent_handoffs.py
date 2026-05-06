"""Tracking-Tabelle für eingehende AgentLink-Handoffs."""
from __future__ import annotations

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def create(
    *,
    incoming_state_id: str,
    from_agent: str,
    agent_id: str,
    session_id: str,
) -> dict:
    row_id = uuid7()
    now = now_iso()
    with db() as conn:
        conn.execute(
            """INSERT INTO agent_handoffs
               (id, incoming_state_id, from_agent, agent_id, session_id, status, started_at)
               VALUES (?, ?, ?, ?, ?, 'running', ?)""",
            (row_id, incoming_state_id, from_agent, agent_id, session_id, now),
        )
    return {
        "id": row_id,
        "incoming_state_id": incoming_state_id,
        "from_agent": from_agent,
        "agent_id": agent_id,
        "session_id": session_id,
        "status": "running",
        "started_at": now,
        "completed_at": None,
    }


def update_status(handoff_id: str, status: str) -> None:
    completed_at = now_iso() if status != "running" else None
    with db() as conn:
        conn.execute(
            "UPDATE agent_handoffs SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, handoff_id),
        )


def list_active() -> list[dict]:
    with db() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        rows = conn.execute(
            "SELECT * FROM agent_handoffs WHERE status = 'running' ORDER BY started_at DESC"
        ).fetchall()
    return rows
