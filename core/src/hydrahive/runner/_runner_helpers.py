"""Hilfsfunktionen für den Runner-Loop."""
from __future__ import annotations

from hydrahive.db import errors_log
from hydrahive.db import messages as messages_db
from hydrahive.runner.events import Error
from hydrahive.tools._sessions import session_end


def close_open_tool_uses(session_id: str, tool_uses: list[dict], reason: str) -> None:
    """Synthetic tool_result blocks for unfinished tool_uses so Anthropic's API
    pairing-check passes on the next turn. Without this the session is poisoned
    and every subsequent send returns 400."""
    blocks = [
        {"type": "tool_result", "tool_use_id": tu.get("id", ""), "content": reason, "is_error": True}
        for tu in tool_uses
        if tu.get("id")
    ]
    if blocks:
        messages_db.append(session_id, "user", blocks)


def refusal_error(session_id, agent, ctx, result, tool_uses, message_id, iteration) -> Error:
    """Beendet den Lauf nach stop_reason=refusal: Tools schließen, loggen, melden."""
    if tool_uses:
        close_open_tool_uses(session_id, tool_uses, "Abgebrochen: Das Modell hat die Antwort abgelehnt (refusal)")
    errors_log.record(
        source="runner.refusal", severity="warning",
        session_id=session_id, agent_id=agent["id"], user_id=ctx.user_id,
        error_type="refusal",
        message=f"stop_reason=refusal in Iteration {iteration + 1} (model={result.used_model})",
        context={"model": result.used_model, "iteration": iteration + 1,
                 "tool_uses": len(tool_uses), "message_id": message_id},
    )
    session_end(agent["id"], session_id, status="abandoned")
    return Error(
        "Das Modell hat die Antwort abgelehnt und abgebrochen (refusal). "
        "Die Arbeit bis hierhin bleibt erhalten. Bitte den Auftrag eingrenzen oder "
        "umformulieren und erneut senden, ggf. ein anderes Modell wählen.",
        metadata={"kind": "refusal", "stop_reason": "refusal",
                  "model": result.used_model, "message_id": message_id},
    )
