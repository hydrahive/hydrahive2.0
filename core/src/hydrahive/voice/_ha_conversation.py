"""Mapping HA-conversation_id → HydraHive-Session-ID.

HA generiert eine eigene conversation_id pro Voice-Konversation und reicht
sie bei jedem Folge-Turn mit. Wir mappen das auf eine HydraHive-Session
damit Folge-Turns auf der gleichen History laufen.

LRU-Cleanup: bei >MAX_ENTRIES wird gekürzt auf KEEP_AFTER_CLEANUP (FIFO).
Storage: voice_conversations.json im Daten-Dir, atomic write.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from hydrahive.db import sessions as sessions_db
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

MAX_ENTRIES = 1000
KEEP_AFTER_CLEANUP = 800

_lock = threading.Lock()


def _path() -> Path:
    return settings.voice_conversations_path


def _load() -> dict[str, dict[str, Any]]:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("voice_conversations.json unlesbar: %s — leer initialisieren", e)
        return {}


def _save(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


def get_or_create_session(
    conversation_id: str,
    *,
    agent_id: str,
    user_id: str,
    project_id: str | None = None,
) -> str:
    """Returns existing session_id for this HA-conversation_id, or creates new.

    Wenn der gemappte session_id nicht mehr in der DB existiert (z. B. user
    hat sie gelöscht), wird transparent eine neue erzeugt.
    """
    with _lock:
        data = _load()
        entry = data.get(conversation_id)
        if entry:
            sid = entry.get("session_id")
            if sid and sessions_db.get(sid):
                return sid
            logger.info(
                "Voice-Session %s (HA-conv %s) nicht mehr in DB — neue erzeugen",
                sid, conversation_id,
            )

        new_session = sessions_db.create(
            agent_id=agent_id,
            user_id=user_id,
            project_id=project_id,
            title=f"Voice (HA): {conversation_id[:8]}",
            metadata={"source": "homeassistant", "ha_conversation_id": conversation_id},
        )
        data[conversation_id] = {
            "session_id": new_session.id,
            "agent_id": agent_id,
        }
        if len(data) > MAX_ENTRIES:
            keep_keys = list(data.keys())[-KEEP_AFTER_CLEANUP:]
            data = {k: data[k] for k in keep_keys}
            logger.info("voice_conversations.json beschnitten: behalten %d", len(data))
        _save(data)
        return new_session.id
