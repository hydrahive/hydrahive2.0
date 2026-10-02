"""Slash-Commands für die Buddy-Page.

Deterministisch im Code — KEIN LLM-Roundtrip. Jede Funktion hier wird von
einem REST-Endpoint aufgerufen und gibt ein Status-Dict für die Frontend-
Anzeige zurück.
"""
from __future__ import annotations

import time
from datetime import datetime

from hydrahive.agents import config as agent_config
from hydrahive.agents._prompt import load_soul
from hydrahive.buddy import _find_buddy_for, _pick_character
from hydrahive.buddy import _soul_state as soul_state
from hydrahive.buddy._commands_helpers import slug as _slug, snapshot_active_session as _snapshot_active_session
from hydrahive.db import sessions as sessions_db
from hydrahive.tools import _memory_store as memory


def _require_buddy(username: str) -> dict:
    buddy = _find_buddy_for(username)
    if not buddy:
        raise LookupError("Kein Buddy für diesen User")
    return buddy


def clear_session(username: str) -> dict:
    """Beendet aktuelle Lifetime-Session, legt neue an. Alte bleibt in DB."""
    buddy = _require_buddy(username)
    # Projekt, Tiefe und Gesprächsmodus übernimmt der gemeinsame Helfer.
    session_id = soul_state.new_session_keeping_project(buddy["id"], username)
    return {
        "ok": True,
        "session_id": session_id,
        "message": "Frischer Chat — neue Session, alte ist im Verlauf gespeichert.",
    }


def remember(username: str, text: str | None = None, name: str | None = None) -> dict:
    """Schreibt einen Memory-Eintrag — ohne LLM.

    - text leer + name leer → Snapshot der aktiven Session unter
      key = `session_<YYYY-MM-DD>` (timestamp-suffix bei Kollision).
    - text gegeben → freie Notiz unter key = `note_<unix>` (oder `<slug(name)>`).
    - name gegeben (egal ob mit text) → key = `<slug(name)>`.
    """
    buddy = _require_buddy(username)
    text = (text or "").strip()
    name = (name or "").strip()

    if not text:
        snapshot = _snapshot_active_session(buddy, username)
        if not snapshot:
            return {"ok": False, "message": "Kein Verlauf zum Speichern."}
        date = datetime.now().strftime("%Y-%m-%d")
        base_key = _slug(name) if name else f"session_{date}"
        key = base_key
        if memory.read_key(buddy["id"], key) is not None:
            key = f"{base_key}_{datetime.now().strftime('%H%M%S')}"
        content = (
            f"# Session {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n{snapshot}"
        )
        memory.write_key(buddy["id"], key, content)
        return {
            "ok": True, "key": key,
            "message": f"Verlauf gespeichert als '{key}' "
                       f"({content.count(chr(10) + chr(10)) + 1} Einträge).",
        }

    key = _slug(name) if name else f"note_{int(time.time())}"
    memory.write_key(buddy["id"], key, text)
    return {"ok": True, "key": key, "message": f"Gespeichert unter '{key}'."}


def list_models(username: str) -> dict:
    """Liefert verfügbare Modelle (live aus dem Katalog-Cache) + aktuelles."""
    buddy = _require_buddy(username)
    from hydrahive.agents._validation import _available_models
    return {"current": buddy.get("llm_model", ""), "available": sorted(_available_models())}


def set_model(username: str, model: str) -> dict:
    """Wechselt das LLM-Modell des Buddy-Agents."""
    model = model.strip()
    if not model:
        raise ValueError("set_model braucht einen Modell-Namen")
    from hydrahive.agents._validation import AgentValidationError, validate_model
    try:
        validate_model(model)
    except AgentValidationError as e:
        raise ValueError(str(e))
    buddy = _require_buddy(username)
    agent_config.update(buddy["id"], llm_model=model)
    return {"ok": True, "model": model, "message": f"Modell auf {model} gewechselt."}


def reroll_character(username: str) -> dict:
    """Würfelt deterministisch einen neuen Charakter (Python random.choice),
    schreibt ihn in Memory + System-Prompt + neue Lifetime-Session.
    Beim nächsten Hi reagiert der Buddy als die neue Figur."""
    buddy = _require_buddy(username)
    universe, character = _pick_character()
    memory.write_key(buddy["id"], soul_state.CHARACTER_KEY,
                     soul_state.format_character(character, universe))
    # Sprache, Ton und Kontext übernehmen, Projektbindung behalten.
    agent_config.set_system_prompt(
        buddy["id"], soul_state.rebuild_soul(username, buddy["id"], universe, character))
    session_id = soul_state.new_session_keeping_project(buddy["id"], username)
    message = f"Neuer Charakter: {character} ({universe}). Sag Hallo."
    soul_active = bool(load_soul(buddy["id"]))
    if soul_active:
        message += (" Achtung: Soul-Dateien sind aktiv und ersetzen den Charakter-Prompt. "
                    "Die neue Figur wirkt erst, wenn die Soul geleert ist.")
    return {"ok": True, "session_id": session_id, "message": message, "soul_active": soul_active}
