from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.mcp import tool_bridge as mcp_bridge
from hydrahive.mcp.client import McpTool, McpToolResult
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools.base import ToolContext

SECRET = "sk-or-v1-" + "x" * 64


@pytest.fixture
def session_message():
    init_db()
    session = sessions_db.create(agent_id="mcp-structured-agent", user_id="admin")
    message = messages_db.append(session.id, "assistant", "tool call")
    context = ToolContext(
        session_id=session.id,
        agent_id="mcp-structured-agent",
        user_id="admin",
        workspace=Path("/tmp"),
    )
    return context, message.id


def test_rohe_strukturfelder_gelangen_nicht_in_runner_oder_tool_calls(
    session_message, monkeypatch,
) -> None:
    context, message_id = session_message
    tool_name = f"{mcp_bridge.PREFIX}rea__inspect"

    async def fake_call(_qualified_name: str, _arguments: dict) -> McpToolResult:
        return McpToolResult(
            success=True,
            content=[{"type": "text", "text": "begrenzte Ansicht"}],
            raw_content=[{"type": "text", "text": f"Rohdaten {SECRET}"}],
            structured_content={"evidence": SECRET},
            meta={"trace": SECRET},
        )

    monkeypatch.setattr(mcp_bridge, "call", fake_call)
    result, record_id, _ = asyncio.run(execute_tool(
        {"name": tool_name, "input": {}, "id": "structured-1"},
        [tool_name], context, message_id,
    ))

    with db() as connection:
        stored = connection.execute(
            "SELECT result FROM tool_calls WHERE id = ?", (record_id,)
        ).fetchone()["result"]

    assert result.output == "begrenzte Ansicht"
    assert SECRET not in json.dumps(result.__dict__)
    assert SECRET not in stored
    assert "evidence" not in stored
    assert "trace" not in stored


def test_gerenderter_mcp_text_wird_weiterhin_an_der_engstelle_geschwaerzt(
    session_message, monkeypatch,
) -> None:
    context, message_id = session_message
    tool_name = f"{mcp_bridge.PREFIX}rea__inspect"

    async def fake_call(_qualified_name: str, _arguments: dict) -> McpToolResult:
        return McpToolResult(
            success=True,
            content=[{"type": "text", "text": f"sichtbar {SECRET}"}],
            raw_content=[{"type": "text", "text": f"sichtbar {SECRET}"}],
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
    monkeypatch.setattr(mcp_bridge, "call", fake_call)
    result, record_id, _ = asyncio.run(execute_tool(
        {"name": tool_name, "input": {}, "id": "structured-2"},
        [tool_name], context, message_id,
    ))

    with db() as connection:
        stored = connection.execute(
            "SELECT result FROM tool_calls WHERE id = ?", (record_id,)
        ).fetchone()["result"]

    assert SECRET not in result.output
    assert "[REDACTED]" in result.output
    assert SECRET not in stored


def test_tool_bridge_bewirbt_keine_outputschemas_oder_metadaten(monkeypatch) -> None:
    async def fake_list_tools(_server_id: str):
        return [McpTool(
            name="inspect",
            description="Sichere Beschreibung",
            schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "default": SECRET},
            annotations={"readOnlyHint": True},
            meta={"credential": SECRET},
        )]

    mcp_bridge._schema_cache.clear()
    monkeypatch.setattr("hydrahive.mcp.manager.list_tools", fake_list_tools)

    schemas = asyncio.run(mcp_bridge.schemas_for_servers(["rea"]))
    encoded = json.dumps(schemas)

    assert SECRET not in encoded
    assert schemas == [{
        "name": "mcp__rea__inspect",
        "description": "Sichere Beschreibung",
        "input_schema": {"type": "object", "properties": {}},
    }]
