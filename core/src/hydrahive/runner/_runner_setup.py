"""Runner — Setup-Helper: Longterm-Memory Tools + System-Prompt-Block."""
from __future__ import annotations


_LONGTERM_MEMORY_PROMPT = (
    "\n\n## Langzeitgedächtnis — PFLICHT\n"
    "Du hast Zugriff auf eine Datenbank mit ALLEN vergangenen Sessions, Gesprächen und Tool-Calls.\n"
    "**Regel: Wenn du etwas nicht weißt oder eine Frage auf vergangene Ereignisse/Personen/Dinge verweist, "
    "rufe ZUERST datamining_search auf — bevor du antwortest oder spekulierst.**\n"
    "Beispiele wann du suchen musst:\n"
    "- Fragen wie 'wie geht es X?', 'was haben wir mit Y gemacht?', 'weißt du noch...?'\n"
    "- Unbekannte Namen, Begriffe oder Referenzen die aus früheren Gesprächen kommen könnten\n"
    "- Aufgaben die du fortsetzen sollst ohne klaren Kontext\n"
    "Tools:\n"
    "- `datamining_search(query, from_date, to_date)` — Volltextsuche; gibt nur neueste Events zurück, "
    "für historische Events immer from_date setzen (z.B. from_date='2026-01-01')!\n"
    "- `datamining_semantic(query)` — semantische Suche, findet auch ohne exakte Worte\n"
    "- `datamining_timeline(from_date, to_date)` — Zeitstrahl aller Sessions in einem Zeitraum, "
    "gruppiert nach Tag mit Gesprächsthemen — ideal für Langzeit-Analyse ohne Keyword\n"
    "- `datamining_today()` — was heute passiert ist\n"
)


def inject_longterm_memory(
    base_system_prompt: str,
    tool_schemas: list[dict],
    allowed_tools: list[str],
) -> str:
    """Fügt die 4 Datamining-Tools + Pflicht-Prompt für Agents mit
    longterm_memory=True hinzu. Mutiert tool_schemas + allowed_tools.

    Returns: erweiterter base_system_prompt.
    """
    from hydrahive.tools.datamining import (
        TOOL_SEARCH, TOOL_SEMANTIC, TOOL_TIMELINE, TOOL_TODAY,
    )
    existing = {s["name"] for s in tool_schemas}
    for tool in (TOOL_SEARCH, TOOL_SEMANTIC, TOOL_TODAY, TOOL_TIMELINE):
        if tool.name not in existing:
            tool_schemas.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.schema,
            })
        if tool.name not in allowed_tools:
            allowed_tools.append(tool.name)
    return base_system_prompt + _LONGTERM_MEMORY_PROMPT
