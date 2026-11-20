"""Abbrechen und Anzeigen von Hintergrund-Aufträgen (für die API)."""
from __future__ import annotations

import logging

from hydrahive.agentlink import cancel_pending
from hydrahive.db import delegations as delegations_db
from hydrahive.db.connection import db
from hydrahive.runner import activity, concurrency

logger = logging.getLogger(__name__)

CANCELLED_TEXT = "Vom Nutzer abgebrochen."


_MAX_CHAIN_DEPTH = 10   # Schutz gegen Zyklen/kaputte Daten; echte Ketten sind 2–3 tief


def cancel(delegation: dict, _depth: int = 0, _seen: set[str] | None = None) -> bool:
    """running → cancelled, Future lösen, Spezialisten-Lauf stoppen – samt der GANZEN Kette darunter.

    Befund 20.11.2026 (Auftrag 5257951b): Abbruch des Projekt-Agenten stoppte nur dessen Lauf; sein
    Frontend-Spezialist arbeitete noch 4 min weiter. Jetzt werden zuerst alle laufenden Aufträge der
    Ziel-Session (rekursiv) abgebrochen, dann deren Lauf gestoppt.
    `cancelled` wird nie zugestellt (der Nutzer wollte es nicht mehr)."""
    if not delegations_db.complete_if_running(delegation["id"], "cancelled", CANCELLED_TEXT):
        return False
    cancel_pending(delegation["state_id"])
    target_sid = delegations_db.target_session_id(delegation["state_id"])
    if target_sid:
        n = _cancel_below(target_sid, _depth, _seen if _seen is not None else set())
        if n:
            logger.info("Hintergrund-Auftrag %s: %d Unter-Auftrag/-Aufträge mit abgebrochen", delegation["id"], n)
        if concurrency.cancel(target_sid):
            logger.info("Hintergrund-Auftrag %s: Spezialisten-Lauf %s gestoppt", delegation["id"], target_sid)
    return True


def _cancel_below(session_id: str, depth: int, seen: set[str]) -> int:
    """Alle laufenden Aufträge, die `session_id` vergeben hat, abbrechen (rekursiv über cancel)."""
    if depth >= _MAX_CHAIN_DEPTH or session_id in seen:
        return 0
    seen.add(session_id)
    n = 0
    for child in delegations_db.list_for_session(session_id, limit=100):
        if child["status"] == "running" and cancel(child, depth + 1, seen):
            n += 1
    return n


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
