"""Slash-Commands für die Buddy-Page.

Deterministisch im Code — KEIN LLM-Roundtrip. Jede Funktion hier wird von
einem REST-Endpoint aufgerufen und gibt ein Status-Dict für die Frontend-
Anzeige zurück.
"""
from __future__ import annotations

import time

from hydrahive.agents import config as agent_config
from hydrahive.buddy import _build_soul, _find_buddy_for, _get_or_create_session
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._config import load_config
from hydrahive.tools import _memory_store as memory


def _require_buddy(username: str) -> dict:
    buddy = _find_buddy_for(username)
    if not buddy:
        raise LookupError("Kein Buddy für diesen User")
    return buddy


def clear_session(username: str) -> dict:
    """Beendet aktuelle Lifetime-Session, legt neue an. Alte bleibt in DB."""
    buddy = _require_buddy(username)
    new_session = sessions_db.create(
        agent_id=buddy["id"], user_id=username,
        title=f"{username}'s Buddy", project_id=None,
    )
    return {
        "ok": True,
        "session_id": new_session.id,
        "message": "Frischer Chat — neue Session, alte ist im Verlauf gespeichert.",
    }


def remember(username: str, text: str) -> dict:
    """Schreibt einen Memory-Eintrag direkt — ohne LLM."""
    text = text.strip()
    if not text:
        raise ValueError("remember braucht einen Text")
    buddy = _require_buddy(username)
    key = f"note_{int(time.time())}"
    memory.write_key(buddy["id"], key, text)
    return {"ok": True, "key": key, "message": f"Gespeichert unter {key}."}


def list_models(username: str) -> dict:
    """Liefert verfügbare Modelle (flat aus allen Providern) + aktuelles."""
    buddy = _require_buddy(username)
    cfg = load_config()
    models: list[str] = []
    for p in cfg.get("providers", []):
        for m in p.get("models", []):
            if m and m not in models:
                models.append(m)
    return {"current": buddy.get("llm_model", ""), "available": models}


def set_model(username: str, model: str) -> dict:
    """Wechselt das LLM-Modell des Buddy-Agents."""
    model = model.strip()
    if not model:
        raise ValueError("set_model braucht einen Modell-Namen")
    available = list_models(username)["available"]
    if model not in available:
        raise ValueError(f"Unbekanntes Modell '{model}'. Verfügbar: {', '.join(available)}")
    buddy = _require_buddy(username)
    agent_config.update(buddy["id"], llm_model=model)
    return {"ok": True, "model": model, "message": f"Modell auf {model} gewechselt."}


def reroll_character(username: str) -> dict:
    """Würfelt einen neuen Charakter: löscht 'character'-Memory + neue Soul +
    neue Session. Beim nächsten Hi stellt sich der Buddy neu vor."""
    buddy = _require_buddy(username)
    memory.delete_key(buddy["id"], "character")
    new_soul = _build_soul(username)
    agent_config.set_system_prompt(buddy["id"], new_soul)
    new_session = sessions_db.create(
        agent_id=buddy["id"], user_id=username,
        title=f"{username}'s Buddy", project_id=None,
    )
    return {
        "ok": True,
        "session_id": new_session.id,
        "message": "Neuer Charakter gewürfelt — sag Hallo.",
    }
