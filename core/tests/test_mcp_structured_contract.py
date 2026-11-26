from __future__ import annotations

from types import SimpleNamespace

from mcp.types import (
    CallToolResult,
    Icon,
    TextContent,
    Tool,
    ToolAnnotations,
    ToolExecution,
)

from hydrahive.mcp.client import McpTool, McpToolResult
from hydrahive.mcp.client.base import result_from_sdk, tool_from_sdk


def test_tool_from_sdk_erhaelt_den_vollstaendigen_vertrag() -> None:
    source = Tool(
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
        execution=ToolExecution(taskSupport="optional"),
        _meta={"provider": "rea"},
    )

    tool = tool_from_sdk(source)

    assert tool == McpTool(
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
        execution={"taskSupport": "optional"},
    )

    tool.meta["provider"] = "changed"
    assert source.meta == {"provider": "rea"}


def test_result_from_sdk_trennt_llm_text_und_originaldaten() -> None:
    source = CallToolResult(
        content=[TextContent(type="text", text="sichtbar")],
        structuredContent={"evidence_id": "ev-1"},
        isError=False,
        _meta={"trace_id": "trace-1"},
    )

    result = result_from_sdk(source)

    assert result == McpToolResult(
        success=True,
        content=[{"type": "text", "text": "sichtbar"}],
        raw_content=[{"type": "text", "text": "sichtbar"}],
        structured_content={"evidence_id": "ev-1"},
        is_error=False,
        meta={"trace_id": "trace-1"},
    )

    result.raw_content[0]["text"] = "changed"
    result.structured_content["evidence_id"] = "changed"
    result.meta["trace_id"] = "changed"
    assert source.content[0].text == "sichtbar"
    assert source.structuredContent == {"evidence_id": "ev-1"}
    assert source.meta == {"trace_id": "trace-1"}


def test_aeltere_sdk_objekte_ohne_optionale_felder_bleiben_lesbar() -> None:
    legacy_tool = SimpleNamespace(
        name="legacy", description=None, inputSchema={"type": "object"},
    )
    legacy_result = SimpleNamespace(
        content=[{"type": "text", "text": "alt"}], isError=False,
    )

    tool = tool_from_sdk(legacy_tool)
    result = result_from_sdk(legacy_result)

    assert tool == McpTool(name="legacy", description="", schema={"type": "object"})
    assert result.content == [{"type": "text", "text": "alt"}]
    assert result.raw_content == [{"type": "text", "text": "alt"}]
    assert result.structured_content is None


def test_alte_konstruktoren_bleiben_rueckwaertskompatibel() -> None:
    tool = McpTool(name="alt", description="", schema={})
    result = McpToolResult(success=True, content=[{"type": "text", "text": "ok"}])

    assert tool.title is None
    assert tool.output_schema is None
    assert tool.annotations is None
    assert tool.icons is None
    assert tool.meta is None
    assert tool.execution is None
    assert result.raw_content == []
    assert result.structured_content is None
    assert result.is_error is False
    assert result.meta is None
