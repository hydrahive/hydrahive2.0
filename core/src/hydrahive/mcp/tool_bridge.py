"""Bridge: MCP-Tools werden für den Runner als ganz normale Tool-Schemas
exponiert. Tool-Naming: `mcp__<server_id>__<original_name>`.
"""
from __future__ import annotations

import logging

from hydrahive.mcp import manager as mcp_manager
from hydrahive.mcp.client import McpToolResult

logger = logging.getLogger(__name__)

PREFIX = "mcp__"
SEP = "__"


def make_tool_name(server_id: str, tool_name: str) -> str:
    return f"{PREFIX}{server_id}{SEP}{tool_name}"


def parse_tool_name(qualified: str) -> tuple[str, str] | None:
    """`mcp__server__tool` → ('server', 'tool'). None wenn nicht MCP."""
    if not qualified.startswith(PREFIX):
        return None
    rest = qualified[len(PREFIX):]
    parts = rest.split(SEP, 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


async def schemas_for_servers(server_ids: list[str]) -> list[dict]:
    """Anthropic-format tool-schemas für alle Tools der angegebenen Server.

    Verbindet bei Bedarf (lazy). Failures pro Server werden geloggt aber
    blockieren nicht die anderen — ein schlechter Server stoppt den Agent nicht.
    """
    out: list[dict] = []
    for sid in server_ids:
        try:
            tools = await mcp_manager.list_tools(sid)
        except Exception as e:
            logger.warning("MCP-Server '%s' Tool-Listing fehlgeschlagen: %s", sid, e)
            continue
        for t in tools:
            out.append({
                "name": make_tool_name(sid, t.name),
                "description": t.description,
                "input_schema": t.schema or {"type": "object", "properties": {}},
            })
    return out


async def call(qualified_name: str, arguments: dict) -> McpToolResult | None:
    """Tool-Call wenn der Name MCP-formatiert ist; sonst None (= nicht für uns)."""
    parsed = parse_tool_name(qualified_name)
    if not parsed:
        return None
    server_id, tool_name = parsed
    try:
        return await mcp_manager.call_tool(server_id, tool_name, arguments)
    except Exception as e:
        return McpToolResult(success=False, error=f"MCP-Aufruf fehlgeschlagen: {e}")
