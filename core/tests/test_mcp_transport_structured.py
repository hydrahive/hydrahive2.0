from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, Icon, TextContent, Tool, ToolAnnotations

from hydrahive.mcp.client import HttpMcpClient, McpTool, SseMcpClient, StdioMcpClient


class FakeSession:
    async def list_tools(self):
        return SimpleNamespace(tools=[
            Tool(
                name="inspect_target",
                title="Inspect Target",
                description="Untersucht ein Ziel",
                inputSchema={"type": "object", "properties": {"path": {"type": "string"}}},
                outputSchema={"type": "object", "properties": {"evidence_id": {"type": "string"}}},
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                icons=[Icon(src="https://example.org/rea.png", mimeType="image/png")],
                _meta={"provider": "rea"},
            )
        ])

    async def call_tool(self, name: str, arguments: dict):
        assert name == "inspect_target"
        assert arguments == {"path": "/work/target"}
        return CallToolResult(
            content=[
                TextContent(type="text", text="sichtbar"),
                TextContent(type="text", text="zweite Zeile"),
            ],
            structuredContent={"evidence_id": "ev-1", "coverage": {"status": "complete"}},
            isError=False,
            _meta={"trace_id": "trace-1"},
        )


class ErrorSession(FakeSession):
    async def call_tool(self, name: str, arguments: dict):
        return CallToolResult(
            content=[TextContent(type="text", text="REA meldet einen Fehler")],
            structuredContent={"code": "unsupported_target"},
            isError=True,
            _meta={"trace_id": "trace-error"},
        )


class CrashingSession(FakeSession):
    async def call_tool(self, name: str, arguments: dict):
        raise TimeoutError("Verbindung beendet")


def _clients():
    return (
        StdioMcpClient(server_id="stdio", command="rea", args=["mcp"]),
        HttpMcpClient(server_id="http", url="http://127.0.0.1/mcp"),
        SseMcpClient(server_id="sse", url="http://127.0.0.1/sse"),
    )


@pytest.mark.parametrize("client", _clients(), ids=("stdio", "http", "sse"))
def test_tooldefinition_bleibt_ueber_alle_transporte_strukturiert(client) -> None:
    client._session = FakeSession()

    tools = asyncio.run(client.list_tools())

    assert tools == [McpTool(
        name="inspect_target",
        description="Untersucht ein Ziel",
        schema={"type": "object", "properties": {"path": {"type": "string"}}},
        title="Inspect Target",
        output_schema={"type": "object", "properties": {"evidence_id": {"type": "string"}}},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        icons=[{"src": "https://example.org/rea.png", "mimeType": "image/png"}],
        meta={"provider": "rea"},
    )]


@pytest.mark.parametrize("client", _clients(), ids=("stdio", "http", "sse"))
def test_toolresultat_behaelt_rohdaten_und_sicheren_textpfad(client) -> None:
    client._session = FakeSession()

    result = asyncio.run(client.call_tool("inspect_target", {"path": "/work/target"}))

    assert result.success is True
    assert result.is_error is False
    assert result.content == [{"type": "text", "text": "sichtbar\nzweite Zeile"}]
    assert result.raw_content == [
        {"type": "text", "text": "sichtbar"},
        {"type": "text", "text": "zweite Zeile"},
    ]
    assert result.structured_content == {
        "evidence_id": "ev-1",
        "coverage": {"status": "complete"},
    }
    assert result.meta == {"trace_id": "trace-1"}
    assert result.error is None


@pytest.mark.parametrize("client", _clients(), ids=("stdio", "http", "sse"))
def test_serverfehler_behaelt_struktur_und_bisherige_fehlersemantik(client) -> None:
    client._session = ErrorSession()

    result = asyncio.run(client.call_tool("inspect_target", {}))

    assert result.success is False
    assert result.is_error is True
    assert result.error == "REA meldet einen Fehler"
    assert result.structured_content == {"code": "unsupported_target"}
    assert result.meta == {"trace_id": "trace-error"}


@pytest.mark.parametrize("client", _clients(), ids=("stdio", "http", "sse"))
def test_transportfehler_liefert_keine_erfundenen_rohdaten(client) -> None:
    client._session = CrashingSession()

    result = asyncio.run(client.call_tool("inspect_target", {}))

    assert result.success is False
    assert result.is_error is True
    assert result.error == "MCP-Call fehlgeschlagen: Verbindung beendet"
    assert result.content == []
    assert result.raw_content == []
    assert result.structured_content is None
    assert result.meta is None
