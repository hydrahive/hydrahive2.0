"""Antwortsprache für alle Agenten aus der Buddy-Einstellung (docs/specs/agent-language.md).

Quelle: `_pref_language` am Buddy des Nutzers, für den der Lauf läuft (Buddy-Einstellungen → Identität → „Sprache“).
Der Block hängt am **stabilen** Prompt-Teil (wie Emote-/Modus-Hinweis): cache-freundlich und unabhängig von der
Kompaktierung – früher stand die Regel nur in Zusammenfassung/Memory und fiel bei einer Kompaktierung weg (05.10.).
`auto` = kein Block (der Agent folgt dem Nutzer). Kein Buddy / unbekannter Wert = Standard der Einstellung (`de`).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "de"
_PREF_KEY = "_pref_language"

# Texte je Sprache gebündelt. `auto` hat bewusst keinen Eintrag.
RULES: dict[str, str] = {
    "de": (
        "## Sprache\n"
        "Antworte immer auf Deutsch. Das gilt für jede Ausgabe, auch für kurze Zwischensätze vor "
        "Werkzeugaufrufen, Rückfragen, Berichte sowie Commit- und PR-Texte. Code, Befehle, Dateinamen und "
        "wörtliche Zitate bleiben im Original. Auch wenn Werkzeug-Ergebnisse, Code oder Logs englisch sind, "
        "bleibt deine Sprache Deutsch."
    ),
    "en": (
        "## Language\n"
        "Always respond in English. This applies to every output, including short sentences before tool calls, "
        "questions, reports, and commit and PR texts. Code, commands, file names and verbatim quotes stay in their "
        "original language. Even if tool results, code or logs are in another language, your language stays English."
    ),
}
VALID = frozenset({*RULES, "auto"})


def language_for(username: str) -> str:
    """Sprache aus dem Buddy des Nutzers; `de`, wenn es keinen Buddy oder keinen gültigen Wert gibt."""
    from hydrahive.agents import config as agent_config
    from hydrahive.tools import _memory_store as memory

    try:
        buddy = next((a for a in agent_config.list_by_owner(username) if a.get("is_buddy")), None)
        value = memory.read_key(buddy["id"], _PREF_KEY) if buddy else None
    except Exception:  # Sprache darf einen Lauf nie verhindern
        logger.warning("Sprach-Einstellung für %s nicht lesbar – Standard %s", username, DEFAULT_LANGUAGE,
                       exc_info=True)
        return DEFAULT_LANGUAGE
    return value if value in VALID else DEFAULT_LANGUAGE


def with_language_rule(base_prompt: str, language: str) -> str:
    """Hängt den Sprach-Block an; bei `auto` unverändert."""
    rule = RULES.get(language)
    return f"{base_prompt}\n\n{rule}" if rule else base_prompt
