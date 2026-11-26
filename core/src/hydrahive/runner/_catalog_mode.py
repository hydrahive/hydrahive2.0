"""tool_mode ``catalog`` (Spec V2/V4/V6/E4, K1/K4/K7): kleine Tool-Liste, der Rest über find_tools/run_tool.

Im catalog-Modus bekommt das Modell nur: Kern ∩ Freigabe, angeheftete und vorgemerkte Tools (alle ∩ Freigabe). Die Freigabe
selbst bleibt ``effective_tool_names``; der Katalog erweitert nie ein Recht. ``allowed_tools`` des Laufs enthält weiter die volle
Freigabe plus die Katalog-Werkzeuge, damit ``run_tool`` alles Freigegebene erreicht.

Harte Regel (E4): Die Tool-Liste und der Prompt ändern sich innerhalb eines Laufs nie. Alles hier wird einmal beim Laufstart
berechnet; Vorgemerktes wirkt erst beim nächsten Lauf.
"""
from __future__ import annotations

import logging

from hydrahive.catalog import CATALOG_TOOLS, CATALOG_TOOLS_ORDERED

logger = logging.getLogger(__name__)

TOOL_MODES = ("classic", "catalog")
DEFAULT_MODE = "classic"

#: Fester Kern (Plan Aufgabe 5, Reihenfolge verbindlich). Schnitt mit der Freigabe; die Katalog-Werkzeuge immer.
CORE_TOOLS: tuple[str, ...] = (
    "shell_exec", "file_read", "file_write", "file_patch", "todo_write",
    *CATALOG_TOOLS_ORDERED,                                   # find_tools, find_skills, run_tool (Namen nur in catalog/)
    "load_skill", "ask_agent", "read_memory", "write_memory", "search_memory",
)

REMEMBER_MAX = 15
METADATA_KEY = "catalog_remembered"


def is_catalog(agent: dict) -> bool:
    return agent.get("tool_mode") == "catalog"


def allowed_with_catalog(effective: list[str]) -> list[str]:
    """Volle Freigabe plus die Katalog-Werkzeuge (kommen im catalog-Modus immer dazu, erweitern aber kein Recht)."""
    return list(effective) + [n for n in CATALOG_TOOLS_ORDERED if n not in effective]


def catalog_schema_names(effective: list[str], pinned: list[str], remembered: list[str]) -> list[str]:
    """Namen der Tools, die ans Modell gehen: (CORE ∩ effective), dann pinned ∩ effective, dann remembered ∩ effective.

    Reihenfolge stabil, keine Duplikate. ``find_tools``/``find_skills``/``run_tool`` sind immer dabei.
    """
    have = set(effective) | CATALOG_TOOLS
    out: list[str] = []
    for group in (CORE_TOOLS, pinned or (), remembered or ()):
        for name in group:
            if name in have and name not in out:
                out.append(name)
    return out


def remembered_for(session) -> list[str]:
    """Vorgemerkte Tools der Sitzung – wird NUR beim Laufstart gelesen (E4)."""
    raw = (getattr(session, "metadata", None) or {}).get(METADATA_KEY)
    return [str(n) for n in raw] if isinstance(raw, list) else []


def remember(session_id: str, tool_name: str) -> None:
    """Merkt ein per run_tool benutztes Tool für den NÄCHSTEN Lauf vor (höchstens REMEMBER_MAX, die ältesten fallen raus).

    Katalog-Werkzeuge selbst werden nie vorgemerkt. Fehler werden nur geloggt – das Vormerken darf einen Lauf nie stören.
    """
    if not tool_name or tool_name in CATALOG_TOOLS:
        return
    try:
        from hydrahive.db import sessions as sessions_db
        sessions_db.remember_catalog_tool(session_id, tool_name, REMEMBER_MAX)
    except Exception:  # noqa: BLE001
        logger.warning("Katalog: Vormerken von %s fehlgeschlagen", tool_name, exc_info=True)


def prompt_block(effective: list[str], skills: list, pinned_skills: list[str]) -> str:
    """Prompt-Abschnitt des catalog-Modus: Hinweis auf die Suche, Kategorien mit mindestens einem eigenen Tool, angeheftete Skills.

    Wird einmal beim Laufstart gebaut und danach unverändert verwendet (E4). Keine Kategorie ohne eigenes Tool.
    """
    from hydrahive.catalog.categories import CATEGORY_LABELS, CATEGORY_MAP
    have = set(effective)
    lines = [
        "## Werkzeuge und Skills bei Bedarf",
        "Du hast nur eine kleine Auswahl an Werkzeugen direkt. Weitere findest du mit `find_tools(query)` und rufst sie mit "
        "`run_tool(name, args)` auf. Skills findest du mit `find_skills(query)` und lädst sie mit `load_skill(name)`.",
    ]
    rows = [f"| `{cat}` | {CATEGORY_LABELS.get(cat, '')} |" for cat in CATEGORY_LABELS
            if have & set(CATEGORY_MAP.get(cat, ()))]
    if rows:
        lines += ["", "## Kategorien", "Dafür gibt es Werkzeuge (per `find_tools` suchen):", "",
                  "| Kategorie | Wofür |", "|-----------|-------|", *rows]
    pinned = [s for s in skills if s.name in set(pinned_skills or [])]
    if pinned:
        lines += ["", "## Angeheftete Skills", "Lade einen Skill mit `load_skill(name)`, wenn er zur Aufgabe passt.", "",
                  "| Skill | Wann nutzen |", "|-------|-------------|",
                  *[f"| `{s.name}` | {s.when_to_use or s.description} |" for s in pinned]]
    return "\n".join(lines)
