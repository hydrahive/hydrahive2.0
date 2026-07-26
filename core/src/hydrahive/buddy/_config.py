"""Buddy-Konfiguration lesen und schreiben (für die Settings-Page)."""

from __future__ import annotations

from hydrahive.agents import _tool_config
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


def _available_tools() -> list[dict]:
    tools = {
        tool.name: {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
        }
        for tool in TOOL_REGISTRY.values()
    }
    for tool in plugin_bridge.all_tool_meta():
        tools.setdefault(tool["name"], tool)
    return sorted(tools.values(), key=lambda item: item["name"])


def get_config(username: str) -> dict:
    buddy = _find_buddy(username)
    bid = buddy["id"]
    available_tools = _available_tools()
    return {
        "agent_id": bid,
        "name": buddy.get("name", ""),
        "model": buddy.get("llm_model", ""),
        "fallback_models": buddy.get("fallback_models", []),
        "temperature": buddy.get("temperature", 1.0),
        "max_tokens": buddy.get("max_tokens", 16_000),
        "thinking_budget": buddy.get("thinking_budget", 0),
        "reasoning_effort": buddy.get("reasoning_effort", ""),
        "character": memory.read_key(bid, "character") or "",
        "tools": buddy.get("tools", []),
        "all_tools": [tool["name"] for tool in available_tools],
        "available_tools": available_tools,
        "mcp_servers": buddy.get("mcp_servers", []),
        "disabled_skills": buddy.get("disabled_skills", []),
        "require_tool_confirm": buddy.get("require_tool_confirm", False),
        "longterm_memory": buddy.get("longterm_memory", False),
        "compact_threshold_pct": buddy.get("compact_threshold_pct", 70),
        "compact_model": buddy.get("compact_model", "") or "",
        "compact_tool_result_limit": buddy.get("compact_tool_result_limit", 8_000),
        "compact_reserve_tokens": buddy.get("compact_reserve_tokens", 20_000),
        "compact_max_turns": buddy.get("compact_max_turns"),
        "tool_result_max_chars": buddy.get("tool_result_max_chars", 0) or 0,
        "max_iterations": buddy.get("max_iterations", 30),
        "cache_ttl": buddy.get("cache_ttl", "5m"),
        "language": memory.read_key(bid, "_pref_language") or "de",
        "tone": memory.read_key(bid, "_pref_tone") or "locker",
        "context": memory.read_key(bid, "_pref_context") or "",
        "tool_config": _tool_config.mask(buddy.get("tool_config")),
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

    if "model" in changes:
        agent_updates["llm_model"] = changes["model"]

    for field in (
        "tools",
        "fallback_models",
        "temperature",
        "max_tokens",
        "thinking_budget",
        "reasoning_effort",
        "mcp_servers",
        "disabled_skills",
        "require_tool_confirm",
        "longterm_memory",
        "compact_threshold_pct",
        "compact_model",
        "compact_tool_result_limit",
        "compact_reserve_tokens",
        "compact_max_turns",
        "tool_result_max_chars",
        "max_iterations",
        "cache_ttl",
    ):
        if field in changes:
            agent_updates[field] = changes[field]

    if "tool_config" in changes:
        # agent_config.update validiert + merged Secrets (leeres Passwort = behalten).
        agent_updates["tool_config"] = changes["tool_config"]

    # Zuerst Agent-Felder validieren und persistieren. So schreiben ungültige
    # Modell-/Runtime-Patches nicht bereits teilweise Soul-Präferenzen.
    if agent_updates:
        agent_config.update(bid, **agent_updates)

    if "language" in changes:
        memory.write_key(bid, "_pref_language", changes["language"])
        soul_dirty = True

    if "tone" in changes:
        memory.write_key(bid, "_pref_tone", changes["tone"])
        soul_dirty = True

    if "context" in changes:
        memory.write_key(bid, "_pref_context", changes["context"])
        soul_dirty = True

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
            agent_id=bid,
            user_id=username,
            title=f"{username}'s Buddy",
            project_id=None,
        )
        return {"ok": True, "new_session_id": new_session.id}

    return {"ok": True, "new_session_id": None}
