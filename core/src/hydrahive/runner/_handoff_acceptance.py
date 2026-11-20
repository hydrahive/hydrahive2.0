"""Kern-Abnahme vor der Fertig-Meldung (agentlink/acceptance.py, docs/specs/chain-anchor.md).

Trägt der eingehende Auftrag Abnahme-Punkte, darf der Lauf nur „done“ melden,
wenn der Bericht jeden Punkt mit ✅ und Beleg enthält. Sonst „incomplete“ –
mit dem Prüfergebnis am Bericht, damit der Auftraggeber sieht, was fehlt.
"""
from __future__ import annotations

import logging

from hydrahive.agentlink import acceptance
from hydrahive.db import agent_handoffs as db_agent_handoffs

logger = logging.getLogger(__name__)
INCOMPLETE = "incomplete"


def apply(handoff_db_id: str, status: str, raw: str, output: str) -> tuple[str, str]:
    """(status, output) nach Abnahmeprüfung. Nur „done“ wird geprüft; Fehler/Pause bleiben, wie sie sind."""
    if status != "done":
        return status, output
    try:
        body = db_agent_handoffs.abnahme_for_handoff(handoff_db_id)
    except Exception:
        logger.exception("Abnahme für Handoff %s nicht lesbar – Fertig-Meldung NICHT bestätigt", handoff_db_id)
        return INCOMPLETE, f"{output}\n\nKern-Abnahmeprüfung: Abnahme nicht lesbar – nicht bestätigt."
    if not body:
        return status, output
    verdict = acceptance.check_report(body, raw)
    logger.info("Abnahme Handoff %s: %d/%d Punkte ✅ mit Beleg", handoff_db_id, len(verdict.ok), len(verdict.required))
    return ("done" if verdict.complete else INCOMPLETE), f"{output}\n\n{verdict.render()}"
