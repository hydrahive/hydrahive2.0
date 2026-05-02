"""Hilfsfunktionen für den Runner-Loop."""
from __future__ import annotations

import logging

from hydrahive.db import messages as messages_db

logger = logging.getLogger(__name__)


def build_skills_block(agent: dict) -> str:
    """Kompakte Liste aller verfügbaren Skills für den Prompt-Header."""
    try:
        from hydrahive.skills import list_for_agent
    except ImportError:
        return ""
    owner = agent.get("owner") or ""
    if not owner:
        return ""
    try:
        skills = list_for_agent(agent["id"], owner, disabled=list(agent.get("disabled_skills", [])))
    except Exception as e:
        logger.warning("Skills laden fehlgeschlagen: %s", e)
        return ""
    if not skills:
        return ""
    lines = [
        "## Verfügbare Skills",
        "Mit `load_skill(name)` lädst du den vollen Body in den Kontext.",
        "Skills können externe Quellen (URLs) deklarieren — diese rufst du mit "
        "`fetch_url(url)` ab; Auth wird automatisch via Credential-Profil-Match "
        "eingehängt (Token landet NICHT im Tool-Result).",
    ]
    for s in skills:
        when = f" — when: {s.when_to_use}" if s.when_to_use else ""
        desc = f": {s.description}" if s.description else ""
        lines.append(f"- **{s.name}**{desc}{when}")
    return "\n".join(lines)


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
