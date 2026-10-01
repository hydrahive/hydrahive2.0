"""Stopp mitten in einer Werkzeug-Runde: Fertiges behalten, Rest ehrlich schließen.

Belegt 30.09.2026 (Session 01a0e01b): Ein fertiges ask_agent-Ergebnis ging
verloren, weil die tool_result-Blöcke erst nach ALLEN Werkzeugen einer Runde
gespeichert wurden. Der Nutzer stoppte während des zweiten Werkzeugs, das
Ergebnis des ersten stand nur in tool_calls, nie im Verlauf. Beim nächsten Turn
hieß es dann „Truncation im vorigen Turn“ und tool_calls blieb auf 'pending'.

Ein Werkzeug, das wirklich nicht fertig wurde, darf nicht als „gelaufen“
gelten, deshalb erhält es is_error=True.
"""
from __future__ import annotations

import logging

from hydrahive.db import messages as messages_db
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

STOPPED_TEXT = "Abgebrochen: Lauf wurde gestoppt, bevor das Werkzeug fertig war."


def persist_on_cancel(
    session_id: str,
    tool_uses: list[dict],
    finished_blocks: list[dict],
    parent_message_id: str,
) -> None:
    """Speichert fertige Blöcke + Stopp-Hinweis für den Rest, markiert pending
    tool_calls als 'cancelled'. Best-effort: ein DB-Fehler darf das Abbrechen
    nicht verhindern."""
    try:
        done_ids = {b.get("tool_use_id") for b in finished_blocks}
        blocks = list(finished_blocks) + [
            {"type": "tool_result", "tool_use_id": tu["id"], "content": STOPPED_TEXT, "is_error": True}
            for tu in tool_uses
            if tu.get("id") and tu.get("id") not in done_ids
        ]
        if blocks:
            messages_db.append(session_id, "user", blocks, metadata={"stopped": True})
        with db() as conn:
            conn.execute(
                "UPDATE tool_calls SET status = 'cancelled', error_message = ? "
                "WHERE message_id = ? AND status = 'pending'",
                (STOPPED_TEXT, parent_message_id),
            )
    except Exception:
        logger.exception("Stopp-Sicherung für Session %s fehlgeschlagen", session_id)
