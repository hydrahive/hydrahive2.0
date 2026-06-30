"""Bridge: MCP-Tools werden für den Runner als ganz normale Tool-Schemas
exponiert. Tool-Naming: `mcp__<server_id>__<original_name>`.
"""
from __future__ import annotations

import asyncio
import logging
import time

from hydrahive.mcp import manager as mcp_manager
from hydrahive.mcp.client import McpToolResult

logger = logging.getLogger(__name__)

PREFIX = "mcp__"
SEP = "__"

_schema_cache: dict[str, tuple[float, list[dict]]] = {}
_SCHEMA_TTL = 60.0


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

    Schemas werden 60s gecached und parallel abgefragt — statt sequentiell
    + doppeltem Health-Probe. Failures pro Server werden geloggt aber
    blockieren nicht die anderen.
    """
    if not server_ids:
        return []

    now = time.monotonic()
    cached: dict[str, list[dict]] = {}
    to_fetch: list[str] = []

    for sid in server_ids:
        entry = _schema_cache.get(sid)
        if entry and (now - entry[0]) < _SCHEMA_TTL:
            cached[sid] = entry[1]
        else:
            to_fetch.append(sid)

    async def _fetch(sid: str) -> tuple[str, list[dict]]:
        try:
            tools = await mcp_manager.list_tools(sid)
            schemas = [
                {
                    "name": make_tool_name(sid, t.name),
                    "description": t.description,
                    "input_schema": t.schema or {"type": "object", "properties": {}},
                }
                for t in tools
            ]
            _schema_cache[sid] = (now, schemas)
            return sid, schemas
        except BaseException as e:  # noqa: BLE001 - anyio TaskGroup wirft BaseExceptionGroup;
            # ein kaputter MCP-Server darf NIE den Agent-Run reißen → hart abfangen.
            logger.warning("MCP-Server '%s' Tool-Listing fehlgeschlagen: %s", sid, e)
            return sid, []

    if to_fetch:
        results = await asyncio.gather(*[_fetch(sid) for sid in to_fetch])
        for sid, schemas in results:
            cached[sid] = schemas

    return [schema for sid in server_ids for schema in cached.get(sid, [])]


async def call(qualified_name: str, arguments: dict) -> McpToolResult | None:
    """Tool-Call wenn der Name MCP-formatiert ist; sonst None (= nicht für uns)."""
    parsed = parse_tool_name(qualified_name)
    if not parsed:
        return None
    server_id, tool_name = parsed
    try:
        return await mcp_manager.call_tool(server_id, tool_name, arguments)
    except BaseException as e:  # noqa: BLE001 - anyio BaseExceptionGroup nicht durchreißen lassen
        return McpToolResult(success=False, error=f"MCP-Aufruf fehlgeschlagen: {e}")
