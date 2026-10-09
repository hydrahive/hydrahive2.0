"""Schutzstufen für Datamining-Sitzungen (docs/specs/knowledge-spaces.md §2.1, Etappe E1a).

Eine Sitzung hat die höchste Stufe aller Werkzeuge, die in ihr benutzt wurden. Bestimmt wird das bei jeder
Suche aus ``events.tool_name`` (Index ``events_tool``) – keine Tabelle, nichts veraltet.
Werkzeug → Stufe: Kernliste hier + ``sensitive_tools`` aus den Manifesten geladener Module.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Reihenfolge = Rang. Ein Agent mit ``max_level`` sieht alle Stufen bis einschließlich dieser.
LEVELS: tuple[str, ...] = ("normal", "privat", "gesundheit")

#: Kern-Werkzeuge (Till, 09.10.: privat = Mail + Cryptoboard-Portfolio; Gesundheit = Patientenakte/Health).
#: Module melden eigene über das Manifest – Patientenakte/Cryptoboard stehen hier, bis ihre Manifeste es tun.
CORE_SENSITIVE: dict[str, str] = {
    "query_fhir_data": "gesundheit",
    "query_health_data": "gesundheit",
    "read_mail": "privat",
    "send_mail": "privat",
    "query_portfolio": "privat",
}


def rank(level: str) -> int:
    """Rang einer Stufe; unbekannt → 0 (normal)."""
    return LEVELS.index(level) if level in LEVELS else 0


def sensitive_tools() -> dict[str, str]:
    """Werkzeug → Stufe aus Kern + geladenen Modulen. Bei Widerspruch gilt die höhere Stufe."""
    out = dict(CORE_SENSITIVE)
    try:
        from hydrahive.modules.registry import REGISTRY
        mods = list(REGISTRY.values())
    except Exception as e:  # noqa: BLE001 — Modul-Registry fehlt (z. B. Tests) → nur Kern
        logger.debug("sensitive_tools: Modul-Registry nicht lesbar: %s", e)
        mods = []
    for m in mods:
        if not (m.loaded and m.manifest):
            continue
        for tool, level in m.manifest.sensitive_tools:
            if rank(level) > rank(out.get(tool, "normal")):
                out[tool] = level
    return out


def hidden_tools(max_level: str) -> list[str]:
    """Werkzeuge, deren Sitzungen ein Agent mit ``max_level`` NICHT sehen darf (sortiert, stabil)."""
    limit = rank(max_level)
    return sorted(t for t, lvl in sensitive_tools().items() if rank(lvl) > limit)
