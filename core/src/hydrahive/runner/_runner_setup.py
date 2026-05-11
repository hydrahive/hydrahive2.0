"""Runner — Setup-Helper: Longterm-Memory Tools + System-Prompt-Block."""
from __future__ import annotations


_LONGTERM_MEMORY_PROMPT = (
    "\n\nLangzeitgedächtnis: für Fragen die konkret auf Vergangenes verweisen, "
    "stehen `datamining_*`-Tools zur Verfügung. Bei generischen Fragen ohne "
    "klaren Vergangenheits-Bezug direkt aus dem Kontext antworten — keine "
    "spekulativen Suchen."
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
