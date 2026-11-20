"""Ablauf einer Handoff-Kette: Antwort zurückhalten, Folgeläufe, Gesamtfrist.

Zustand liegt in runner/handoff_session.py. Lauf und Antwort selbst bleiben in
runner/handoff_receiver.py (_run_and_reply, _finish); sie werden hier erst zur
Laufzeit importiert, weil handoff_receiver dieses Modul importiert.
(docs/specs/agent-background-delegation.md, Abschnitt „Kette über Handoff“)
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.agentlink.protocol import State
from hydrahive.runner import handoff_session
from hydrahive.runner._run_origin import RunOrigin

logger = logging.getLogger(__name__)


def hold_reply(state: State, session_id: str, handoff_db_id: str, run_timeout: int | None,
               origin: RunOrigin | None, raw: str, failure_kind: str | None) -> bool:
    """True = Antwort zurückhalten, weil noch Kind-Aufträge offen sind.

    Nur bei origin handoff. Echter Fehler im Lauf → sofort antworten, offene
    Kinder abbrechen (nichts läuft verwaist weiter). Iterationsgrenze bei
    offenen Kindern ist kein Abbruch: der Lauf hat verteilt, die Kette wartet
    (sonst würde ein Checkpoint auf eine Session ohne ihre Kinder zeigen).
    ``failure_kind`` = None (kein Fehler) | "max_iterations" | sonstiger Fehler."""
    if origin is None or origin.kind != "handoff":
        return False
    failed = failure_kind is not None
    if failed and not (failure_kind == "max_iterations" and handoff_session.running_children(session_id)):
        handoff_session.cancel_children(session_id)
        return False
    if not handoff_session.has_pending_work(session_id):
        return False
    chain = handoff_session.get(session_id)
    if chain is None:
        chain = handoff_session.ChainState(
            state=state, session_id=session_id, handoff_db_id=handoff_db_id,
            run_timeout=run_timeout, depth=origin.depth,
            started=handoff_session.started_at(session_id),
        )
        handoff_session.open_chain(chain)
        chain.deadline_task = asyncio.create_task(
            _deadline(session_id), name=f"handoff-chain-deadline-{session_id}")
    if raw.strip():
        chain.last_output = raw
    from hydrahive.runner import delegation_delivery
    # call_soon: erst nach Lauf-Ende (Guard frei), sonst sieht kick die Session als laufend.
    asyncio.get_running_loop().call_soon(_kick_when_free, session_id, delegation_delivery)
    logger.info("Handoff-Kette %s: %d Kind-Auftrag/-Aufträge offen, Antwort zurückgehalten",
                session_id, handoff_session.running_children(session_id))
    return True


def _kick_when_free(session_id: str, delivery) -> None:
    """Zustellung anstoßen, sobald der Lauf-Guard frei ist (Guard wird erst nach
    _run_and_reply-Ende in _consume_run freigegeben → kurz nachfassen)."""
    from hydrahive.runner.concurrency import is_running
    if not handoff_session.is_open(session_id):
        return
    if is_running(session_id):
        asyncio.get_running_loop().call_later(0.2, _kick_when_free, session_id, delivery)
        return
    delivery.kick(session_id)


def continue_chain(session_id: str, user_input: str, *, depth: int) -> bool:
    """Von delegation_delivery: Kind-Ergebnis(se) in einem Folgelauf auswerten.
    False = keine offene Kette für diese Session (dann normaler Chat-Starter)."""
    chain = handoff_session.get(session_id)
    if chain is None:
        return False
    from hydrahive.runner import handoff_tasks
    from hydrahive.runner._run_origin import handoff as origin_handoff
    from hydrahive.runner.handoff_receiver import _run_and_reply
    task = asyncio.create_task(
        _run_and_reply(chain.state, session_id, chain.handoff_db_id, run_timeout=chain.run_timeout,
                       # Tiefe der Kette, nicht +1 je Runde: Grenze ist hier die Gesamtfrist
                       # (CHAIN_TOTAL_SECONDS), sonst hätte der Projekt-Agent nur 2 Runden.
                       origin=origin_handoff(chain.depth), user_input=user_input),
        name=f"handoff-followup-{session_id}",
    )
    handoff_tasks.register(f"followup-{session_id}-{id(task)}", task)
    return True


async def _deadline(session_id: str) -> None:
    """Gesamtfrist: danach mit dem bisherigen Stand antworten, Kinder abbrechen."""
    chain = handoff_session.get(session_id)
    if chain is None:
        return
    await asyncio.sleep(max(0.0, chain.remaining()))
    if handoff_session.get(session_id) is not chain:
        return
    from hydrahive.runner.concurrency import cancel as cancel_run
    from hydrahive.runner.concurrency import is_running
    if is_running(session_id):
        # Folgelauf läuft gerade: abbrechen. Sein CancelledError-Zweig antwortet
        # mit Checkpoint; die Kette wird dort geschlossen.
        chain.deadline_hit = True
        handoff_session.cancel_children(session_id)
        cancel_run(session_id)
        return
    handoff_session.close_chain(session_id)
    n = handoff_session.cancel_children(session_id)
    minutes = handoff_session.CHAIN_TOTAL_SECONDS // 60
    logger.warning("Handoff-Kette %s: Gesamtfrist abgelaufen, %d Kind-Auftrag/-Aufträge abgebrochen",
                   session_id, n)
    from hydrahive.runner.handoff_receiver import RunFailure, _finish
    await _finish(chain.state, session_id, chain.handoff_db_id, chain.last_output,
                  RunFailure(f"Gesamtfrist von {minutes} min abgelaufen — {n} Spezialisten-Auftrag/-Aufträge "
                             "abgebrochen. Bisheriger Stand steht oben."))


def cancel_cause(chain: handoff_session.ChainState | None) -> tuple[str, str, str]:
    """Warum wurde der Lauf abgebrochen? (Anzeige, verbleibende Arbeit, Checkpoint-Grund)."""
    if chain is not None and chain.deadline_hit:
        minutes = handoff_session.CHAIN_TOTAL_SECONDS // 60
        return (f"Gesamtfrist von {minutes} min abgelaufen (kein Server-Neustart).",
                "Begonnenen Auftrag fortsetzen (Frist neu) und Ergebnis verifizieren.", "deadline")
    return ("Server-Neustart oder Stopp während der Bearbeitung.",
            "Begonnenen Auftrag nach Server-Neustart fortsetzen und Ergebnis verifizieren.", "shutdown")
