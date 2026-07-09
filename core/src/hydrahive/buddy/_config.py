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

_PREF_COCKPIT = "_pref_cockpit"
_COCKPIT_SLOT_IDS = ("music", "extensions", "moduleWidgets", "futureBottom")
_DECOR_VARIANTS = {"default", "calm", "aurora", "minimal"}

DEFAULT_COCKPIT_PREFS = {
    "version": 1,
    "slots": {
        "music": {"visible": True, "collapsed": True},
        "extensions": {"visible": True, "collapsed": True},
        "moduleWidgets": {"visible": True, "collapsed": False},
        "futureBottom": {"visible": False, "collapsed": True},
    },
    "rightRailCollapsed": False,
    "decorVariant": "default",
}


def _bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def normalize_cockpit_prefs(raw: object | None) -> dict:
    source = raw if isinstance(raw, dict) else {}
    raw_slots = source.get("slots") if isinstance(source.get("slots"), dict) else {}
    slots = {}
    for slot_id in _COCKPIT_SLOT_IDS:
        default_slot = DEFAULT_COCKPIT_PREFS["slots"][slot_id]
        incoming = raw_slots.get(slot_id) if isinstance(raw_slots.get(slot_id), dict) else {}
        slots[slot_id] = {
            "visible": _bool(incoming.get("visible"), default_slot["visible"]),
            "collapsed": _bool(incoming.get("collapsed"), default_slot["collapsed"]),
        }
    decor = source.get("decorVariant")
    return {
        "version": 1,
        "slots": slots,
        "rightRailCollapsed": _bool(source.get("rightRailCollapsed"), DEFAULT_COCKPIT_PREFS["rightRailCollapsed"]),
        "decorVariant": decor if decor in _DECOR_VARIANTS else DEFAULT_COCKPIT_PREFS["decorVariant"],
    }


def get_cockpit_prefs(username: str) -> dict:
    buddy = _find_buddy(username)
    return normalize_cockpit_prefs(memory.read_key(buddy["id"], _PREF_COCKPIT))


def put_cockpit_prefs(username: str, prefs: dict) -> dict:
    buddy = _find_buddy(username)
    normalized = normalize_cockpit_prefs(prefs)
    memory.write_key(buddy["id"], _PREF_COCKPIT, normalized)
    return normalized


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

    if "tools" in changes:
        agent_updates["tools"] = changes["tools"]

    for field in ("compact_threshold_pct", "compact_model", "tool_result_max_chars"):
        if field in changes:
            agent_updates[field] = changes[field]

    if "tool_config" in changes:
        # agent_config.update validiert + merged Secrets (leeres Passwort = behalten).
        agent_updates["tool_config"] = changes["tool_config"]

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
