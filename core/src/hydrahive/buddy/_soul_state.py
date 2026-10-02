"""Buddys Soul aus gespeicherten Einstellungen neu aufbauen — ohne LLM.

Figur, Sprache, Ton und Kontext liegen im Agent-Memory. Beim Neuwürfeln der
Figur und beim Ändern der Einstellungen muss der Soul aus *allen* Bausteinen
entstehen, sonst gehen Sprache, Ton oder Kontext verloren.
"""
from __future__ import annotations

from hydrahive.tools import _memory_store as memory

CHARACTER_KEY = "character"
_SEP = " (aus "


def format_character(character: str, universe: str) -> str:
    return f"{character}{_SEP}{universe})"


def parse_character(raw: str) -> tuple[str, str] | None:
    """„Figur (aus Welt)“ → (Welt, Figur). Am letzten „ (aus “ trennen, damit
    Figuren mit Klammern im Namen („Marlin (Findet Nemo)“) erhalten bleiben."""
    raw = (raw or "").strip()
    head, sep, tail = raw.rpartition(_SEP)
    if not sep or not head.strip() or not tail.endswith(")"):
        return None
    return tail[:-1].strip(), head.strip()


def preferences(agent_id: str) -> tuple[str, str, str]:
    """(language, tone, context) mit denselben Defaults wie die Settings-Page."""
    return (
        memory.read_key(agent_id, "_pref_language") or "de",
        memory.read_key(agent_id, "_pref_tone") or "locker",
        memory.read_key(agent_id, "_pref_context") or "",
    )


def rebuild_soul(username: str, agent_id: str, universe: str, character: str) -> str:
    """Soul mit der angegebenen Figur und den gespeicherten Präferenzen."""
    from hydrahive.buddy import _build_soul

    language, tone, context = preferences(agent_id)
    return _build_soul(username, universe, character, language, tone, context)


# Nutzer-Einstellungen der Session, kein Gesprächsinhalt — gehen in jede
# Nachfolge-Session über (Frischer Chat, Einstellungen speichern, Neuwürfeln).
_KEEP_METADATA = ("reasoning_effort", "buddy_mode")


def new_session_keeping_project(agent_id: str, username: str) -> str:
    """Neue Buddy-Session; Projektbindung, Tiefe und Gesprächsmodus der
    aktuellen Session bleiben erhalten. Die neue wird zur aktuellen."""
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy.sessions_picker import current_session, remember
    from hydrahive.db import sessions as sessions_db

    buddy = agent_config.get(agent_id) or {"id": agent_id}
    current = current_session(buddy, username)
    project_id = current.project_id if current else None
    old_md = (current.metadata or {}) if current else {}
    keep = {k: old_md[k] for k in _KEEP_METADATA if old_md.get(k)}
    new_id = sessions_db.create(
        agent_id=agent_id, user_id=username,
        title=f"{username}'s Buddy", project_id=project_id, metadata=keep or None,
    ).id
    remember(agent_id, new_id)
    return new_id
