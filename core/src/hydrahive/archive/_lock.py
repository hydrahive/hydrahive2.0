"""Schritt 1 „Sperren“ (Spec archiv-system.md, Etappe 2).

Agenten auf `disabled` (der Runner startet dann nichts Neues, runner.py prüft status != active),
laufende Läufe abbrechen, Projekt-Freigabe aus. Der alte Zustand wird gemerkt und steht im
Auftrag, damit `release()` ihn auch nach einem Neustart wiederherstellen kann.
"""
from __future__ import annotations

import logging

from hydrahive.agents import config as agent_config

logger = logging.getLogger(__name__)


def stop_run(session_id: str) -> None:
    """Laufenden Agent-Lauf abbrechen (wie der Stopp-Knopf). Eigene Funktion, damit Tests sie ersetzen können."""
    from hydrahive.runner import concurrency
    concurrency.cancel(session_id)


def lock(agents: list[dict], session_ids: list[str], project_ids: list[str]) -> dict:
    """Sperrt und gibt den alten Zustand zurück: {"agents": {id: status}, "shares": [project_id]}."""
    from hydrahive.samba import disable_share, is_share_enabled
    state: dict = {"agents": {}, "shares": []}
    for a in agents:
        state["agents"][a["id"]] = a.get("status") or "active"
        if a.get("status") != "disabled":
            agent_config.update(a["id"], status="disabled")
    for sid in session_ids:
        stop_run(sid)
    for pid in project_ids:
        if is_share_enabled(pid):
            state["shares"].append(pid)
            disable_share(pid)
    return state


def release(state: dict, project_names: dict[str, str]) -> None:
    """Vorherigen Zustand wiederherstellen (Fehler vor dem Löschen oder Abbruch durch Neustart)."""
    from hydrahive.samba import enable_share
    for agent_id, status in (state.get("agents") or {}).items():
        try:
            if agent_config.get(agent_id):
                agent_config.update(agent_id, status=status)
        except Exception:  # noqa: BLE001 – ein kaputter Agent darf die anderen nicht blockieren
            logger.exception("Status von Agent %s ließ sich nicht zurücksetzen", agent_id)
    for pid in state.get("shares") or []:
        enable_share(pid, project_names.get(pid, pid))
