"""Abbrechen und Anzeigen von Hintergrund-Aufträgen (für die API)."""
from __future__ import annotations

import logging

from hydrahive.agentlink import cancel_pending
from hydrahive.db import delegations as delegations_db
from hydrahive.db.connection import db
from hydrahive.runner import activity, concurrency

logger = logging.getLogger(__name__)

CANCELLED_TEXT = "Vom Nutzer abgebrochen."


def cancel(delegation: dict) -> bool:
    """running → cancelled, Future lösen, Spezialisten-Lauf stoppen.
    `cancelled` wird nie zugestellt (der Nutzer wollte es nicht mehr)."""
    if not delegations_db.complete_if_running(delegation["id"], "cancelled", CANCELLED_TEXT):
        return False
    cancel_pending(delegation["state_id"])
    target_sid = delegations_db.target_session_id(delegation["state_id"])
    if target_sid and concurrency.cancel(target_sid):
        logger.info("Hintergrund-Auftrag %s: Spezialisten-Lauf %s gestoppt", delegation["id"], target_sid)
    return True


def _rounds(session_id: str | None) -> int:
    if not session_id:
        return 0
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM llm_calls WHERE session_id = ?", (session_id,),
        ).fetchone()
    return int(row[0])


def _current_tool(session_id: str | None, owner: str) -> str | None:
    if not session_id:
        return None
    for a in activity.snapshot(owner):
        if a["session_id"] == session_id:
            return a.get("current_tool")
    return None


def serialize(d: dict, owner: str) -> dict:
    target_sid = d.get("target_session_id")
    running = d["status"] == "running"
    return {
        "id": d["id"],
        "target_agent_id": d["target_agent_id"],
        "target_name": d["target_name"],
        "task": d["task"][:200],
        "status": d["status"],
        "depth": d["depth"],
        "created_at": d["created_at"],
        "deadline_at": d["deadline_at"],
        "finished_at": d["finished_at"],
        "delivered": d["delivered_at"] is not None,
        "target_session_id": target_sid,
        "rounds": _rounds(target_sid) if running else None,
        "current_tool": _current_tool(target_sid, owner) if running else None,
    }
