"""Welche Unterhaltung zeigt Buddy — und frühere wieder öffnen.

Spec docs/specs/buddy-session-picker.md. Die gewählte Unterhaltung steht in der
Buddy-Konfiguration (``active_session_id``), nicht im Agent-Memory: das liest der
Agent selbst und würde den Merker für einen Fakt halten.
"""
from __future__ import annotations

from hydrahive.agents import config as agent_config
from hydrahive.db import _buddy_sessions as web
from hydrahive.db import sessions as sessions_db

ACTIVE_KEY = "active_session_id"
_MAX_PAGE = 100


class RunActive(RuntimeError):
    """In der aktuellen Unterhaltung läuft gerade ein Lauf."""


def current_session(buddy: dict, username: str) -> sessions_db.Session | None:
    """Gemerkte Web-Sitzung, sonst die jüngste. Ungültige Merker werden entfernt."""
    remembered = buddy.get(ACTIVE_KEY)
    if remembered:
        s = web.get_web(buddy["id"], username, remembered)
        if s:
            return s
        agent_config.update(buddy["id"], **{ACTIVE_KEY: ""})
    return web.newest_web(buddy["id"], username)


def remember(buddy_id: str, session_id: str) -> None:
    agent_config.update(buddy_id, **{ACTIVE_KEY: session_id})


def _buddy(username: str) -> dict:
    from hydrahive.buddy import _find_buddy_for

    buddy = _find_buddy_for(username)
    if not buddy:
        raise LookupError("Kein Buddy für diesen User")
    return buddy


def list_sessions(username: str, *, offset: int = 0, limit: int = 30) -> dict:
    buddy = _buddy(username)
    limit = max(1, min(_MAX_PAGE, int(limit)))
    active = current_session(buddy, username)
    active_id = active.id if active else None
    items, has_more = web.list_web(
        buddy["id"], username, offset=max(0, int(offset)), limit=limit, keep_id=active_id,
    )
    return {"sessions": items, "active_id": active_id, "has_more": has_more}


def open_session(username: str, session_id: str) -> dict:
    """Frühere Unterhaltung zur aktuellen machen; liefert den neuen Buddy-Zustand."""
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.runner import concurrency

    buddy = _buddy(username)
    if not web.get_web(buddy["id"], username, session_id):
        raise LookupError("Unterhaltung nicht gefunden")
    active = current_session(buddy, username)
    if active and active.id != session_id and concurrency.is_running(active.id):
        raise RunActive("In der aktuellen Unterhaltung läuft gerade etwas")
    remember(buddy["id"], session_id)
    return get_or_create_buddy(username)
