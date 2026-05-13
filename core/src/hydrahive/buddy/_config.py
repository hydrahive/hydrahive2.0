"""Buddy-Konfiguration lesen und schreiben (für die Settings-Page)."""
from __future__ import annotations

from hydrahive.agents import config as agent_config
from hydrahive.buddy._characters import pick_character as _pick_character
from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.tools import REGISTRY as TOOL_REGISTRY
from hydrahive.tools import _memory_store as memory


def _find_buddy(username: str) -> dict:
    for a in agent_config.list_by_owner(username):
        if a.get("is_buddy"):
            return a
    raise LookupError("Kein Buddy für diesen User")


def get_config(username: str) -> dict:
    buddy = _find_buddy(username)
    bid = buddy["id"]
    all_tools = (
        [t.name for t in TOOL_REGISTRY.values()]
        + [t["name"] for t in plugin_bridge.all_tool_meta()]
    )
    return {
        "name": buddy.get("name", ""),
        "model": buddy.get("llm_model", ""),
        "character": memory.read_key(bid, "character") or "",
        "tools": buddy.get("tools", []),
        "all_tools": all_tools,
        "compact_threshold_pct": buddy.get("compact_threshold_pct", 70),
        "compact_model": buddy.get("compact_model", "") or "",
        "tool_result_max_chars": buddy.get("tool_result_max_chars", 0) or 0,
        "language": memory.read_key(bid, "_pref_language") or "de",
        "tone": memory.read_key(bid, "_pref_tone") or "locker",
        "context": memory.read_key(bid, "_pref_context") or "",
    }


def patch_config(username: str, changes: dict) -> dict:
    """Wendet Teiländerungen an. Baut Soul neu wenn Sprache/Ton/Kontext ändern."""
    from hydrahive.buddy import _build_soul
    from hydrahive.db import sessions as sessions_db

    buddy = _find_buddy(username)
    bid = buddy["id"]

    soul_dirty = False
    agent_updates: dict = {}

    if "name" in changes:
        agent_updates["name"] = changes["name"]

    if "tools" in changes:
        agent_updates["tools"] = changes["tools"]

    for field in ("compact_threshold_pct", "compact_model", "tool_result_max_chars"):
        if field in changes:
            agent_updates[field] = changes[field]

    if "language" in changes:
        memory.write_key(bid, "_pref_language", changes["language"])
        soul_dirty = True

    if "tone" in changes:
        memory.write_key(bid, "_pref_tone", changes["tone"])
        soul_dirty = True

    if "context" in changes:
        memory.write_key(bid, "_pref_context", changes["context"])
        soul_dirty = True

    if agent_updates:
        agent_config.update(bid, **agent_updates)

    if soul_dirty:
        character_raw = memory.read_key(bid, "character") or ""
        if "(" in character_raw and "aus" in character_raw:
            char_name = character_raw.split("(")[0].strip()
            universe = character_raw.split("aus")[-1].rstrip(")").strip()
        else:
            universe, char_name = _pick_character()
        language = memory.read_key(bid, "_pref_language") or "de"
        tone = memory.read_key(bid, "_pref_tone") or "locker"
        context = memory.read_key(bid, "_pref_context") or ""
        new_soul = _build_soul(username, universe, char_name, language, tone, context)
        agent_config.set_system_prompt(bid, new_soul)
        new_session = sessions_db.create(
            agent_id=bid, user_id=username,
            title=f"{username}'s Buddy", project_id=None,
        )
        return {"ok": True, "new_session_id": new_session.id}

    return {"ok": True, "new_session_id": None}
