"""SSE-MCP-Client (legacy Server-Sent-Events-Transport)."""
from __future__ import annotations

import logging
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from hydrahive.mcp.client.base import McpTool, McpToolResult, render_tool_content

logger = logging.getLogger(__name__)


class SseMcpClient:
    """Verbindet sich gegen einen SSE-MCP-Endpoint."""

    def __init__(self, *, server_id: str, url: str, headers: dict[str, str] | None = None):
        self.server_id = server_id
        self._url = url
        self._headers = dict(headers or {})
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> None:
        if self._session is not None:
            return
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(
                sse_client(self._url, headers=self._headers)
            )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception as e:
            await stack.aclose()
            raise e
        self._stack = stack
        self._session = session
        logger.info("MCP %s verbunden (sse: %s)", self.server_id, self._url)

    async def list_tools(self) -> list[McpTool]:
        if not self._session:
            raise RuntimeError(f"MCP-Client '{self.server_id}' nicht verbunden")
        resp = await self._session.list_tools()
        return [
            McpTool(name=t.name, description=t.description or "",
                    schema=getattr(t, "inputSchema", {}) or {})
            for t in resp.tools
        ]

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
