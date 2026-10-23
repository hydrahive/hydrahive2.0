"""Hilfe-Assistent: aktuelle Seite des Nutzers als System-Kontext (docs/plans/help-assistant.md, Schritt 5).

Der Pfad kommt aus dem Browser – also nur ein sauberer, kurzer, interner Pfad (/…), ohne Abfrage, Anker,
Zeilenumbrüche oder Sonderzeichen. Sonst „unbekannt“. So kann keine Anweisung über den Pfad in den Prompt gelangen.
"""
from __future__ import annotations

import re

from hydrahive.helpdesk import _manual as manual

_PATH = re.compile(r"^/[A-Za-z0-9/_.-]{0,159}$")

# Erster Pfad-Abschnitt → Hilfe-Thema (nur wo der Name abweicht; sonst gleicher Name, wenn es den Artikel gibt).
_TOPIC_FOR = {"": "dashboard", "settings": "settings", "help": "onboarding", "m": "modules", "llm": "llm"}
_SETTINGS = {"agents": "agents", "projects": "projects", "credentials": "credentials", "users": "users",
             "system": "system", "extensions": "extensions", "modules": "modules", "access": "access"}


def clean_path(raw: str | None) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = raw.split("?", 1)[0].split("#", 1)[0]
    if path.startswith("//") or not _PATH.match(path):
        return None
    return path


def topic_for(path: str | None, lang: str = "de") -> str | None:
    if not path:
        return None
    parts = [p for p in path.split("/") if p]
    first = parts[0] if parts else ""
    topic = _SETTINGS.get(parts[1], "settings") if first == "settings" and len(parts) > 1 else \
        _TOPIC_FOR.get(first, first)
    return topic if topic in manual.topics(lang) else None


def context_block(raw_path: str | None, lang: str = "de") -> str:
    path = clean_path(raw_path)
    lines = ["## Aktuelle Seite", f"Aktuelle Seite: {path or 'unbekannt'}"]
    topic = topic_for(path, lang)
    if topic:
        lines.append(f"Passendes Hilfe-Thema: {topic} (mit help_read lesen)")
    return "\n".join(lines)
