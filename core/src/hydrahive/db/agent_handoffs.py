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


def get_resumable(
    handoff_id: str, *, from_agent: str, agent_id: str,
) -> dict | None:
    """Read a caller-/target-bound paused handoff without consuming it."""
    with db() as conn:
        row = conn.execute(
            """SELECT * FROM agent_handoffs
               WHERE id = ? AND from_agent = ? AND agent_id = ? AND status = 'paused'""",
            (handoff_id, from_agent, agent_id),
        ).fetchone()
    return dict(row) if row else None


def claim_resumable(
    handoff_id: str, *, from_agent: str, agent_id: str,
) -> dict | None:
    """Atomically consume one paused handoff bound to its caller and target."""
    with db(immediate=True) as conn:
        row = conn.execute(
            """SELECT * FROM agent_handoffs
               WHERE id = ? AND from_agent = ? AND agent_id = ? AND status = 'paused'""",
            (handoff_id, from_agent, agent_id),
        ).fetchone()
        if not row:
            return None
        changed = conn.execute(
            """UPDATE agent_handoffs SET status = 'resumed'
               WHERE id = ? AND status = 'paused'""",
            (handoff_id,),
        ).rowcount
        return dict(row) if changed == 1 else None


def restore_paused_claim(handoff_id: str) -> bool:
    """Roll back a claim when resume setup fails before the run is scheduled."""
    with db(immediate=True) as conn:
        changed = conn.execute(
            """UPDATE agent_handoffs SET status = 'paused'
               WHERE id = ? AND status = 'resumed'""",
            (handoff_id,),
        ).rowcount
    return changed == 1


def list_active() -> list[dict]:
    with db() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        rows = conn.execute(
            "SELECT * FROM agent_handoffs WHERE status = 'running' ORDER BY started_at DESC"
        ).fetchall()
    return rows
