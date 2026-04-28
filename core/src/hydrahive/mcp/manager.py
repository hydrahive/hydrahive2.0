"""Connection-Pool für MCP-Clients.

Hält je Server-ID höchstens einen verbundenen Client. Hybrid-Modell:
explizit per `connect()`, dann liegt die Verbindung warm; `get_or_connect()`
holt sie raus, verbindet bei Bedarf nach.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from hydrahive.mcp import config as mcp_config
from hydrahive.mcp._validation import McpValidationError
from hydrahive.mcp.client import (
    HttpMcpClient,
    McpClient,
    McpTool,
    McpToolResult,
    SseMcpClient,
    StdioMcpClient,
)

logger = logging.getLogger(__name__)

_clients: dict[str, McpClient] = {}
_lock = asyncio.Lock()


def _build(server_cfg: dict) -> McpClient:
    transport = server_cfg.get("transport")
    sid = server_cfg["id"]
    if transport == "stdio":
        return StdioMcpClient(
            server_id=sid,
            command=server_cfg["command"],
            args=server_cfg.get("args", []),
            env=server_cfg.get("env", {}),
        )
    if transport == "http":
        return HttpMcpClient(
            server_id=sid,
            url=server_cfg["url"],
            headers=server_cfg.get("headers", {}),
        )
    if transport == "sse":
        return SseMcpClient(
            server_id=sid,
            url=server_cfg["url"],
            headers=server_cfg.get("headers", {}),
        )
    raise McpValidationError(f"Unbekannter Transport: {transport}")


async def connect(server_id: str) -> McpClient:
    """Explizit verbinden — liefert den verbundenen Client."""
    async with _lock:
        existing = _clients.get(server_id)
        if existing and existing.is_connected:
            return existing
        cfg = mcp_config.get(server_id)
        if not cfg:
            raise KeyError(f"MCP-Server '{server_id}' nicht in der Registry")
        client = _build(cfg)
        await client.connect()
        _clients[server_id] = client
        return client


async def get_or_connect(server_id: str) -> McpClient:
    """Lazy: liefert verbundenen Client, verbindet falls nötig."""
    existing = _clients.get(server_id)
    if existing and existing.is_connected:
        return existing
    return await connect(server_id)


async def disconnect(server_id: str) -> bool:
    async with _lock:
        client = _clients.pop(server_id, None)
        if not client:
            return False
        await client.close()
        return True


async def disconnect_all() -> None:
    async with _lock:
        ids = list(_clients.keys())
    for sid in ids:
        await disconnect(sid)


def status() -> list[dict]:
    """Snapshot des Pools für /api/mcp/servers."""
    return [
        {"id": sid, "connected": c.is_connected}
        for sid, c in _clients.items()
    ]


async def list_tools(server_id: str) -> list[McpTool]:
    client = await get_or_connect(server_id)
    return await client.list_tools()


async def call_tool(server_id: str, tool_name: str, arguments: dict) -> McpToolResult:
    client = await get_or_connect(server_id)
    return await client.call_tool(tool_name, arguments)
