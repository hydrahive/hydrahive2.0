"""Abstrakte Schnittstelle für MCP-Clients über alle Transports."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class McpTool:
    name: str
    description: str
    schema: dict
    title: str | None = None
    output_schema: dict | None = None
    annotations: dict | None = None
    icons: list[dict] | None = None
    meta: dict | None = None
    execution: dict | None = None


@dataclass
class McpToolResult:
    success: bool
    # Rückwärtskompatibler, bewusst begrenzter Textpfad für Runner/LLM.
    content: list[dict] = field(default_factory=list)
    error: str | None = None
    # Verlustfreie Felder für vertrauenswürdige Control-Planes wie den REA-Gateway.
    # Der normale Runner persistiert oder bewirbt sie absichtlich nicht.
    raw_content: list[dict] = field(default_factory=list)
    structured_content: dict | None = None
    is_error: bool = False
    meta: dict | None = None


class McpClient(Protocol):
    """Eine Verbindung zu einem MCP-Server. Lifecycle: connect → list_tools → call_tool* → close."""

    server_id: str

    async def connect(self) -> None: ...
    async def list_tools(self) -> list[McpTool]: ...
    async def call_tool(self, name: str, arguments: dict) -> McpToolResult: ...
    async def close(self) -> None: ...
    @property
    def is_connected(self) -> bool: ...


def _json_value(value: Any) -> Any:
    """SDK-/Pydantic-Werte als eigenständige JSON-nahe Strukturen kopieren."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return deepcopy(value)


def _optional_dict(value: Any) -> dict | None:
    if value is None:
        return None
    copied = _json_value(value)
    return copied if isinstance(copied, dict) else None


def tool_from_sdk(tool: Any) -> McpTool:
    """Ein MCP-SDK-Tool verlustfrei in den transportneutralen Vertrag überführen."""
    raw = _json_value(tool)
    if not isinstance(raw, dict):
        raw = {}
    return McpTool(
        name=str(raw.get("name", getattr(tool, "name", ""))),
        description=str(raw.get("description", getattr(tool, "description", "")) or ""),
        schema=raw.get("inputSchema", getattr(tool, "inputSchema", {})) or {},
        title=raw.get("title", getattr(tool, "title", None)),
        output_schema=raw.get("outputSchema", getattr(tool, "outputSchema", None)),
        annotations=_optional_dict(raw.get("annotations", getattr(tool, "annotations", None))),
        icons=raw.get("icons", getattr(tool, "icons", None)),
        meta=_optional_dict(raw.get("_meta", getattr(tool, "meta", None))),
        execution=_optional_dict(raw.get("execution", getattr(tool, "execution", None))),
    )


def result_from_sdk(response: Any) -> McpToolResult:
    """MCP-Resultat vollständig erhalten, LLM-Text aber separat begrenzen."""
    blocks = list(getattr(response, "content", None) or [])
    text = render_tool_content(blocks)
    is_error = bool(getattr(response, "isError", False))
    return McpToolResult(
        success=not is_error,
        content=[{"type": "text", "text": text}],
        error=text if is_error else None,
        raw_content=[_json_value(block) for block in blocks],
        structured_content=_optional_dict(getattr(response, "structuredContent", None)),
        is_error=is_error,
        meta=_optional_dict(getattr(response, "meta", None)),
    )


def render_tool_content(blocks: list[Any]) -> str:
    """Standard-Rendering der Tool-Antwort für die LLM-Konversation."""
    parts: list[str] = []
    for block in blocks:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, dict):
            parts.append(str(block))
        else:
            parts.append(str(block))
    return "\n".join(part for part in parts if part)
