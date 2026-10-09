"""Manifest-Feld ``sensitive_tools`` (docs/specs/knowledge-spaces.md §2.1).

Ein Modul meldet damit, welche seiner Werkzeuge eine Sitzung sensibel machen::

    "sensitive_tools": {"query_portfolio": "privat"}

Erlaubte Stufen: ``privat``, ``gesundheit`` (``normal`` braucht keinen Eintrag). Ohne Angabe: nichts.
"""
from __future__ import annotations

import re

LEVELS = ("privat", "gesundheit")
_TOOL_RE = re.compile(r"^[a-zA-Z0-9_]{1,80}$")
MAX_TOOLS = 100


def parse_sensitive_tools(value: object, error: type[Exception]) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise error("manifest.json: 'sensitive_tools' muss ein Objekt {werkzeug: stufe} sein")
    if len(value) > MAX_TOOLS:
        raise error(f"manifest.json: 'sensitive_tools' höchstens {MAX_TOOLS} Einträge")
    out: list[tuple[str, str]] = []
    for tool, level in value.items():
        if not isinstance(tool, str) or not _TOOL_RE.match(tool):
            raise error(f"manifest.json: ungültiger Werkzeugname in 'sensitive_tools': {tool!r}")
        if level not in LEVELS:
            raise error(f"manifest.json: 'sensitive_tools.{tool}' muss eins von {LEVELS} sein, nicht {level!r}")
        out.append((tool, level))
    return tuple(sorted(out))
