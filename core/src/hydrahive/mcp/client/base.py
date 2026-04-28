"""Abstrakte Schnittstelle für MCP-Clients über alle Transports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class McpTool:
    name: str
    description: str
    schema: dict


@dataclass
class McpToolResult:
    success: bool
    content: list[dict] = field(default_factory=list)
    error: str | None = None


class McpClient(Protocol):
    """Eine Verbindung zu einem MCP-Server. Lifecycle: connect → list_tools → call_tool* → close."""

    server_id: str

    async def connect(self) -> None: ...
    async def list_tools(self) -> list[McpTool]: ...
    async def call_tool(self, name: str, arguments: dict) -> McpToolResult: ...
    async def close(self) -> None: ...
    @property
    def is_connected(self) -> bool: ...


def render_tool_content(blocks: list[Any]) -> str:
    """Standard-Rendering der Tool-Antwort für die LLM-Konversation."""
    parts: list[str] = []
    for b in blocks:
        if hasattr(b, "text"):
            parts.append(b.text)
        elif isinstance(b, dict) and b.get("type") == "text":
            parts.append(b.get("text", ""))
        elif isinstance(b, dict):
            parts.append(str(b))
        else:
            parts.append(str(b))
    return "\n".join(p for p in parts if p)
