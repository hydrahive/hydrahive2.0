"""Hilfsfunktionen für den Runner-Loop."""
from __future__ import annotations

from hydrahive.db import messages as messages_db


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
