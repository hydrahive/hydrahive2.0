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
    read_memory,
    search_memory,
    send_mail,
    shell,
    todo,
    web_search,
    write_memory,
)
from hydrahive.tools.base import Tool, ToolContext, ToolResult


REGISTRY: dict[str, Tool] = {
    t.name: t
    for t in [
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
        ask_agent.TOOL,
        send_mail.TOOL,
    ]
}


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
