"""stdio-MCP-Client — Subprocess-Kommunikation über stdin/stdout."""
from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from hydrahive.mcp.client.base import McpTool, McpToolResult, render_tool_content

logger = logging.getLogger(__name__)


class StdioMcpClient:
    """One subprocess per server. The session lives until close() is called.

    Uses AsyncExitStack to manage the cascading stdio → ClientSession contexts;
    that keeps the subprocess alive between method calls. `connect()` sets up,
    `close()` tears down.
    """

    def __init__(self, *, server_id: str, command: str, args: list[str], env: dict[str, str] | None = None):
        self.server_id = server_id
        self._command = command
        self._args = list(args)
        self._env = {**os.environ, **(env or {})}
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> None:
        if self._session is not None:
            return
        params = StdioServerParameters(command=self._command, args=self._args, env=self._env)
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception:
            await stack.aclose()
            raise
        self._stack = stack
        self._session = session
        logger.info("MCP %s verbunden (stdio: %s)", self.server_id, self._command)

    async def list_tools(self) -> list[McpTool]:
        if not self._session:
            raise RuntimeError(f"MCP-Client '{self.server_id}' nicht verbunden")
        resp = await self._session.list_tools()
        out: list[McpTool] = []
        for t in resp.tools:
            out.append(McpTool(
                name=t.name,
                description=t.description or "",
                schema=t.inputSchema if hasattr(t, "inputSchema") else {},
            ))
        return out

    async def call_tool(self, name: str, arguments: dict) -> McpToolResult:
        if not self._session:
            raise RuntimeError(f"MCP-Client '{self.server_id}' nicht verbunden")
        try:
            resp = await self._session.call_tool(name, arguments)
        except Exception as e:
            return McpToolResult(success=False, error=f"MCP-Call fehlgeschlagen: {e}")
        text = render_tool_content(resp.content or [])
        is_error = bool(getattr(resp, "isError", False))
        return McpToolResult(
            success=not is_error,
            content=[{"type": "text", "text": text}],
            error=text if is_error else None,
        )

    async def close(self) -> None:
        if self._stack:
            try:
                await self._stack.aclose()
            except Exception as e:
                logger.warning("MCP %s Close-Fehler: %s", self.server_id, e)
        self._stack = None
        self._session = None
        logger.info("MCP %s getrennt", self.server_id)
