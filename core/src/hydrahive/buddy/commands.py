"""Slash-Commands für die Buddy-Page.

Deterministisch im Code — KEIN LLM-Roundtrip. Jede Funktion hier wird von
einem REST-Endpoint aufgerufen und gibt ein Status-Dict für die Frontend-
Anzeige zurück.
"""
from __future__ import annotations

import re
import time
from datetime import datetime

from hydrahive.agents import config as agent_config
from hydrahive.buddy import _build_soul, _find_buddy_for, _pick_character
from hydrahive.db import messages as messages_db
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


_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def _slug(s: str) -> str:
    return _SLUG_RE.sub("-", s.strip().lower()).strip("-") or "note"


def _extract_text_from_content(content) -> str:
    """Aus DB-Message-content (str oder list[ContentBlock]) den Text-Anteil
    konkatenieren. Tool-Use/Tool-Result werden ausgelassen."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                t = b.get("text", "")
                if t:
                    parts.append(t)
        return " ".join(parts).strip()
    return ""


def _snapshot_active_session(buddy: dict, username: str, last_n: int = 30) -> str:
    """Markdown-Dump der letzten N user/assistant-Messages aus der aktiven
    Lifetime-Session des Buddys."""
    sessions = [s for s in sessions_db.list_for_user(username)
                if s.agent_id == buddy["id"]]
    if not sessions:
        return ""
    sessions.sort(key=lambda s: s.created_at, reverse=True)
    msgs = messages_db.list_for_session(sessions[0].id)
    msgs = [m for m in msgs if m.role in ("user", "assistant")][-last_n:]
    lines: list[str] = []
    for m in msgs:
        text = _extract_text_from_content(m.content)
        if not text:
            continue
        who = "User" if m.role == "user" else buddy.get("name", "Buddy")
        lines.append(f"**{who}:** {text}")
    return "\n\n".join(lines)


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
    """Würfelt deterministisch einen neuen Charakter (Python random.choice),
    schreibt ihn in Memory + System-Prompt + neue Lifetime-Session.
    Beim nächsten Hi reagiert der Buddy als die neue Figur."""
    buddy = _require_buddy(username)
    universe, character = _pick_character()
    memory.write_key(buddy["id"], "character", f"{character} (aus {universe})")
    new_soul = _build_soul(username, universe, character)
    agent_config.set_system_prompt(buddy["id"], new_soul)
    new_session = sessions_db.create(
        agent_id=buddy["id"], user_id=username,
        title=f"{username}'s Buddy", project_id=None,
    )
    return {
        "ok": True,
        "session_id": new_session.id,
        "message": f"Neuer Charakter: {character} ({universe}). Sag Hallo.",
    }
