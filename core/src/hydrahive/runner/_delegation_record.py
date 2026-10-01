"""Ergebnis eines Hintergrund-Auftrags direkt aus dem Receiver speichern.

Läuft im selben Prozess wie der Auftraggeber: Das Ergebnis landet in
agent_delegations, unabhängig davon, ob die AgentLink-Antwort ankommt
(docs/specs/agent-background-delegation.md, Task 620bb0de).
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.agentlink.checkpoints import split_checkpoint_findings
from hydrahive.agentlink.protocol import State
from hydrahive.db import delegations as delegations_db
from hydrahive.runner import delegation_delivery
from hydrahive.runner._handoff_reply import bounded_reply

logger = logging.getLogger(__name__)


def record_delegation_result(
    state: State, status: str, output: str, checkpoint: str | None,
) -> None:
    """Hintergrund-Auftrag aus demselben Prozess: Ergebnis direkt in die DB.
    Unabhängig davon, ob die AgentLink-Antwort ankommt (34 verlorene
    Fehler-Antworten seit 15.09., Task 620bb0de). Best-effort."""
    if not state.id:
        return
    try:
        text = bounded_reply(output)
        if checkpoint:
            _vis, cp = split_checkpoint_findings([checkpoint])
            if cp:
                text += (
                    "\nFortsetzen: ask_agent für denselben agent_id mit "
                    f"resume_token=\"{cp['resume_token']}\" aufrufen."
                )
        row = delegations_db.complete_by_state(state.id, status, text)
        if row:
            asyncio.get_running_loop().call_soon(delegation_delivery.kick, row["session_id"])
    except Exception:
        logger.exception("handoff_receiver: Delegations-Ergebnis für %s nicht gespeichert", state.id)
