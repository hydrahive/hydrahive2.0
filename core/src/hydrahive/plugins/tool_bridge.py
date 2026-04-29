"""Plugin-Tools für den Runner als ganz normale Tool-Schemas exponieren.

Tool-Naming: `plugin__<plugin-name>__<tool-name>`. Analog zu MCP.
"""
from __future__ import annotations

import logging

from hydrahive.plugins.registry import REGISTRY
from hydrahive.tools.base import ToolContext, ToolResult

logger = logging.getLogger(__name__)

PREFIX = "plugin__"
SEP = "__"


def make_tool_name(plugin_name: str, tool_name: str) -> str:
    return f"{PREFIX}{plugin_name}{SEP}{tool_name}"


def parse_tool_name(qualified: str) -> tuple[str, str] | None:
    """`plugin__name__tool` → ('name', 'tool'). None wenn nicht Plugin-Tool."""
    if not qualified.startswith(PREFIX):
        return None
    rest = qualified[len(PREFIX):]
    parts = rest.split(SEP, 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def all_tool_meta() -> list[dict]:
    """Für `_meta/tools` — alle Plugin-Tools mit Name + Description."""
    out: list[dict] = []
    for plugin in REGISTRY.values():
        if not plugin.loaded:
            continue
        for tool in plugin.tools:
            out.append({
                "name": make_tool_name(plugin.name, tool.name),
                "description": tool.description,
            })
    return out


def schemas_for(qualified_names: list[str]) -> list[dict]:
    """Anthropic-format-Schemas der angeforderten Plugin-Tools."""
    by_name: dict[str, tuple] = {}
    for plugin in REGISTRY.values():
        if not plugin.loaded:
            continue
        for tool in plugin.tools:
            by_name[make_tool_name(plugin.name, tool.name)] = tool
    out: list[dict] = []
    for q in qualified_names:
        tool = by_name.get(q)
        if not tool:
            continue
        out.append({
            "name": q,
            "description": tool.description,
            "input_schema": tool.schema,
        })
    return out


async def call(qualified_name: str, args: dict, tool_ctx: ToolContext) -> ToolResult | None:
    """Routet einen Plugin-Tool-Call. Returns None wenn nicht für uns."""
    parsed = parse_tool_name(qualified_name)
    if not parsed:
        return None
    plugin_name, tool_name = parsed
    plugin = REGISTRY.get(plugin_name)
    if not plugin or not plugin.loaded:
        return ToolResult.fail(f"Plugin '{plugin_name}' nicht geladen")
    for tool in plugin.tools:
        if tool.name == tool_name:
            try:
                return await tool.execute(args, tool_ctx)
            except Exception as e:
                logger.exception("Plugin-Tool '%s' crashte", qualified_name)
                return ToolResult.fail(f"Plugin-Crash: {type(e).__name__}: {e}")
    return ToolResult.fail(f"Tool '{tool_name}' im Plugin '{plugin_name}' nicht gefunden")
