"""Zustellung fertiger Hintergrund-Aufträge an die Session des Auftraggebers.

`kick(session_id)` wird aufgerufen, wenn ein Auftrag fertig wird (Watcher) und
wenn ein Chat-Lauf normal endet (start_run_task). Ist die Session frei und
wartet etwas, startet ein Zustell-Lauf (RunOrigin delegation) mit allen
wartenden Ergebnissen in EINER Nachricht.

Nach einem Stopp durch den Nutzer wird nicht automatisch zugestellt (`pause`):
Wer stoppt, will nicht, dass sofort wieder etwas startet. Die nächste eigene
Nachricht (`resume`) oder der Knopf „Jetzt auswerten“ (`auto=False`) hebt das auf.

Der Starter (api/routes/_session_msg_helpers.start_run_task) wird von lifespan
per `configure` gesetzt — die Runner-Schicht importiert die API nicht.
"""
from __future__ import annotations

import logging
from typing import Callable

from hydrahive.db import delegations as delegations_db
from hydrahive.runner import concurrency
from hydrahive.runner._delegation_message import build_metadata, build_text
from hydrahive.runner._run_origin import delegation

logger = logging.getLogger(__name__)

_start_run: Callable | None = None
_paused: set[str] = set()


def configure(start_run: Callable | None) -> None:
    global _start_run
    _start_run = start_run


def pause(session_id: str) -> None:
    _paused.add(session_id)


def resume(session_id: str) -> None:
    _paused.discard(session_id)


def is_paused(session_id: str) -> bool:
    return session_id in _paused


def kick(session_id: str, *, auto: bool = True) -> bool:
    """Startet einen Zustell-Lauf, falls Ergebnisse warten. True = gestartet.

    Synchron ohne await: is_running-Prüfung, claim und Task-Start laufen im
    Event-Loop ohne Unterbrechung, deshalb kein Doppelstart."""
    if _start_run is None:
        return False
    if auto and session_id in _paused:
        return False
    if concurrency.is_running(session_id):
        return False  # Hook nach Lauf-Ende übernimmt
    try:
        claimed = delegations_db.claim_undelivered(session_id)
    except Exception:
        logger.exception("Zustellung: claim für Session %s fehlgeschlagen", session_id)
        return False
    if not claimed:
        return False
    ids = [d["id"] for d in claimed]
    depth = max(int(d.get("depth") or 1) for d in claimed)
    try:
        _start_run(
            session_id, build_text(claimed),
            origin=delegation(depth), user_metadata=build_metadata(claimed, depth),
        )
    except concurrency.SessionAlreadyRunning:
        delegations_db.unclaim(ids)
        return False
    except Exception:
        logger.exception("Zustellung: Lauf für Session %s nicht gestartet", session_id)
        delegations_db.unclaim(ids)
        return False
    resume(session_id)
    logger.info("Zustellung: %d Ergebnis(se) an Session %s", len(ids), session_id)
    return True
