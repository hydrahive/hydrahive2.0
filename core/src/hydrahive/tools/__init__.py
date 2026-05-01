"""Core-Tools für HydraHive2-Agenten.

Jedes Tool ist ein eigenes Modul mit einem `TOOL`-Objekt. Die Registry
unten importiert alle und stellt sie dem Runner zur Verfügung.

Public API:
    REGISTRY                    — dict[name, Tool]
    list_tools()                — alle Tools
    get_tool(name)              — einzelnes Tool, raises KeyError
    schemas_for(names)          — JSON-Schemas für LLM (Anthropic-Format)
"""

from hydrahive.tools import (
    ask_agent,
    dir_list,
    file_patch,
    file_read,
    file_search,
    file_write,
    http_request,
    list_projects,
    list_skills,
    load_skill,
    read_memory,
    search_memory,
    send_mail,
    shell,
    todo,
    web_search,
    write_memory,
)
from hydrahive.settings import settings
from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _build_registry() -> dict[str, Tool]:
    """Liste der aktiven Tools. ask_agent nur wenn AgentLink konfiguriert ist —
    sonst sieht der Master ein Tool das immer mit einem Stub-Fehler antwortet,
    was Loop-Detection triggern und Iterationen verschwenden kann (#13)."""
    tools: list[Tool] = [
        shell.TOOL,
        file_read.TOOL,
        file_write.TOOL,
        file_patch.TOOL,
        file_search.TOOL,
        dir_list.TOOL,
        web_search.TOOL,
        http_request.TOOL,
        read_memory.TOOL,
        write_memory.TOOL,
        search_memory.TOOL,
        todo.TOOL,
        send_mail.TOOL,
        list_projects.TOOL,
        list_skills.TOOL,
        load_skill.TOOL,
    ]
    if settings.agentlink_url:
        tools.append(ask_agent.TOOL)
    return {t.name: t for t in tools}


REGISTRY: dict[str, Tool] = _build_registry()

# Tools die je nach Setup conditional registriert werden. Auf der Validation-
# Ebene werden sie toleriert — der Runner filtert sie über schemas_for() ohnehin
# raus wenn nicht in REGISTRY. Verhindert Validation-Fail bei bestehenden
# Agent-Configs nachdem AgentLink z.B. aus HH_AGENTLINK_URL entfernt wird (#78).
OPTIONAL_TOOLS: frozenset[str] = frozenset({"ask_agent"})


def list_tools() -> list[Tool]:
    return list(REGISTRY.values())


def get_tool(name: str) -> Tool:
    return REGISTRY[name]


def schemas_for(names: list[str]) -> list[dict]:
    """Anthropic-format tool schemas: {name, description, input_schema}."""
    out = []
    for name in names:
        tool = REGISTRY.get(name)
        if not tool:
            continue
        out.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.schema,
        })
    return out


__all__ = [
    "REGISTRY",
    "Tool",
    "ToolContext",
    "ToolResult",
    "list_tools",
    "get_tool",
    "schemas_for",
]
