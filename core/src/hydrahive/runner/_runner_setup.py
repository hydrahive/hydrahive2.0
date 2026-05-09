"""Runner — Setup-Helper: Longterm-Memory Tools + System-Prompt-Block."""
from __future__ import annotations


_LONGTERM_MEMORY_PROMPT = (
    "\n\n## Langzeitgedächtnis\n"
    "Du hast Zugriff auf eine Datenbank mit vergangenen Sessions, Gesprächen und Tool-Calls "
    "über die `datamining_*`-Tools. Nutze sie wenn die Frage konkret auf etwas Vergangenes "
    "verweist — z.B. \"wie ging es mit X weiter\", \"was haben wir damals zu Y entschieden\", "
    "unbekannte Namen aus früheren Sessions. Bei generischen Fragen ohne klaren Vergangenheits-"
    "Bezug ist eine Suche nicht nötig — antworte dann direkt aus dem Kontext.\n"
    "\n"
    "**Empty-Search-Budget**: wenn zwei aufeinanderfolgende `datamining_search`-Calls "
    "`count: 0` zurückgeben, hör auf weitere Query-Variationen zu probieren. Sag dem User "
    "ehrlich, dass nichts gefunden wurde, und antworte mit dem was du sonst weißt. "
    "Brute-Force durch Synonyme verschwendet nur Tokens.\n"
    "\n"
    "Tools:\n"
    "- `datamining_timeline(from_date, to_date)` — **erste Wahl** wenn der User nach einem "
    "Zeitraum fragt (\"letzte Woche\", \"gestern\"). Zeigt Sessions gruppiert nach Tag mit "
    "Themen, ohne dass du raten musst nach welchen Begriffen zu suchen ist.\n"
    "- `datamining_search(query, from_date, to_date)` — Volltextsuche. Für historische "
    "Events immer `from_date` setzen.\n"
    "- `datamining_today()` — was heute passiert ist\n"
    "- `datamining_semantic(query)` — semantische Suche (nur wenn Embedding-Modell "
    "konfiguriert; sonst nicht im Tool-Set sichtbar)\n"
)


def inject_longterm_memory(
    base_system_prompt: str,
    tool_schemas: list[dict],
    allowed_tools: list[str],
) -> str:
    """Fügt Datamining-Tools + Memory-Prompt für Agents mit
    longterm_memory=True hinzu. Mutiert tool_schemas + allowed_tools.

    `datamining_semantic` wird nur registriert wenn ein embed_model in der
    LLM-Config gesetzt ist — sonst würde der Tool-Call mit "Embedding
    fehlgeschlagen" enden und unnötig Tokens kosten.

    Returns: erweiterter base_system_prompt.
    """
    from hydrahive.llm._config import load_config
    from hydrahive.tools.datamining import (
        TOOL_SEARCH, TOOL_SEMANTIC, TOOL_TIMELINE, TOOL_TODAY,
    )

    embed_model = load_config().get("embed_model", "").strip()
    available_tools = [TOOL_SEARCH, TOOL_TODAY, TOOL_TIMELINE]
    if embed_model:
        available_tools.append(TOOL_SEMANTIC)

    existing = {s["name"] for s in tool_schemas}
    for tool in available_tools:
        if tool.name not in existing:
            tool_schemas.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.schema,
            })
        if tool.name not in allowed_tools:
            allowed_tools.append(tool.name)
    return base_system_prompt + _LONGTERM_MEMORY_PROMPT
