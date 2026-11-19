"""Handoff-Aufträge über mehrere Läufe (Kette Buddy → Projekt-Agent → Spezialist).

Ein per AgentLink beauftragter Agent darf selbst Spezialisten im Hintergrund
beauftragen (origin ``handoff``). Seine Antwort an den Auftraggeber geht dann
erst raus, wenn KEINE Kind-Delegation mehr offen ist:

1. Erster Lauf endet, Kind-Delegationen laufen noch → Antwort zurückhalten.
2. Ein Kind-Ergebnis ist da → ``delegation_delivery`` startet hier einen
   Auswertungslauf (statt eines Chat-Laufs), der Agent wertet aus und vergibt
   ggf. weitere Aufträge.
3. Lauf endet, nichts mehr offen → EINE Antwort mit dem letzten Bericht.

Grenzen: Jeder einzelne Lauf hat das Template-Budget des Agenten. Für den
ganzen Auftrag gilt die Gesamtfrist (``CHAIN_TOTAL_SECONDS``). Läuft sie ab,
wird mit dem bisherigen Stand geantwortet, offene Kind-Aufträge werden
abgebrochen. Nichts wartet unbegrenzt.
(docs/specs/agent-background-delegation.md, Abschnitt „Kette über Handoff“)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from hydrahive.agentlink.protocol import State
from hydrahive.agentlink.runtime_profiles import CHAIN_TOTAL_SECONDS

logger = logging.getLogger(__name__)

__all__ = ["CHAIN_TOTAL_SECONDS", "ChainState"]


@dataclass
class ChainState:
    """Ein laufender Handoff-Auftrag, dessen Antwort noch aussteht."""
    state: State
    session_id: str
    handoff_db_id: str
    run_timeout: int | None
    depth: int
    started: float = field(default_factory=time.monotonic)
    last_output: str = ""
    deadline_task: asyncio.Task | None = None

    def remaining(self) -> float:
        return CHAIN_TOTAL_SECONDS - (time.monotonic() - self.started)


# session_id → Startzeit des Handoff-Auftrags (monotonic). Die Gesamtfrist zählt
# ab dem Eingang des Auftrags, nicht erst ab Ende des ersten Laufs.
_started: dict[str, float] = {}


def mark_started(session_id: str) -> None:
    _started[session_id] = time.monotonic()


def started_at(session_id: str) -> float:
    return _started.get(session_id, time.monotonic())


def forget(session_id: str) -> None:
    _started.pop(session_id, None)


# session_id → offener Auftrag. Nur im Speicher: Ein Server-Neustart beendet
# ihn ohnehin (reconcile setzt Handoffs und Delegationen auf error/lost).
_open: dict[str, ChainState] = {}


def get(session_id: str) -> ChainState | None:
    return _open.get(session_id)


def is_open(session_id: str) -> bool:
    return session_id in _open


def open_chain(chain: ChainState) -> None:
    _open[chain.session_id] = chain


def close_chain(session_id: str) -> ChainState | None:
    chain = _open.pop(session_id, None)
    _started.pop(session_id, None)
    if chain and chain.deadline_task and not chain.deadline_task.done():
        if chain.deadline_task is not _current_task():
            chain.deadline_task.cancel()
    return chain


def _current_task():
    try:
        return asyncio.current_task()
    except RuntimeError:
        return None


def running_children(session_id: str) -> int:
    from hydrahive.db import delegations as delegations_db
    return delegations_db.count_running(session_id)


def has_pending_work(session_id: str) -> bool:
    """Offen = Kind läuft noch ODER fertiges Ergebnis wartet auf Auswertung."""
    from hydrahive.db import delegations as delegations_db
    return running_children(session_id) > 0 or delegations_db.has_undelivered(session_id)


def cancel_children(session_id: str) -> int:
    """Gesamtfrist abgelaufen: offene Kind-Aufträge abbrechen (nichts läuft verwaist weiter)."""
    from hydrahive.db import delegations as delegations_db
    from hydrahive.runner import delegation_control
    n = 0
    for d in delegations_db.list_for_session(session_id, limit=100):
        if d["status"] == "running" and delegation_control.cancel(d):
            n += 1
    return n
