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
    datamining,
    file_patch,
    file_read,
    file_write,
    fetch_url,
    health_data,
    list_projects,
    list_skills,
    load_skill,
    read_memory,
    search_memory,
    send_mail,
    shell,
    todo,
    web_browser,
    web_search,
    webmin_call,
    webmin_status,
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
        web_search.TOOL,
        fetch_url.TOOL,
        health_data.TOOL,
        read_memory.TOOL,
        write_memory.TOOL,
        search_memory.TOOL,
        todo.TOOL,
        send_mail.TOOL,
        list_projects.TOOL,
        list_skills.TOOL,
        load_skill.TOOL,
        datamining.TOOL_SEARCH,
        datamining.TOOL_SEMANTIC,
        datamining.TOOL_TIMELINE,
        datamining.TOOL_TODAY,
    ]
    if settings.agentlink_url:
        tools.append(ask_agent.TOOL)
    tools.append(web_browser.TOOL)
    if settings.webmin_url:
        tools.append(webmin_status.TOOL)
        tools.append(webmin_call.TOOL)
    return {t.name: t for t in tools}


REGISTRY: dict[str, Tool] = _build_registry()

# Tools die je nach Setup conditional registriert werden. Auf der Validation-
# Ebene werden sie toleriert — der Runner filtert sie über schemas_for() ohnehin
# raus wenn nicht in REGISTRY. Verhindert Validation-Fail bei bestehenden
# Agent-Configs nachdem AgentLink z.B. aus HH_AGENTLINK_URL entfernt wird (#78).
# ask_agent: nur aktiv wenn AgentLink konfiguriert
# file_search, dir_list, http_request: entfernte Tools — in alten Configs tolerieren
OPTIONAL_TOOLS: frozenset[str] = frozenset({"ask_agent", "web_browser", "file_search", "dir_list", "http_request", "webmin_status", "webmin_call"})


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
