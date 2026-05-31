"""Wiring-Test: execute_tool schwärzt Secrets an der Engstelle.

Beweist die Regression des realen Vorfalls: ein Agent dumpt einen Provider-Key
in den Tool-Output (hier via Fake-Tool, im echten Fall via `env`/`cat config`).
execute_tool muss den Key schwärzen, BEVOR er zurückgegeben UND in die
tool_calls-DB geschrieben wird — beide Persistenz-Pfade.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import REGISTRY
from hydrahive.tools.base import Tool, ToolContext, ToolResult

LONG_KEY = "sk-or-v1-" + "b" * 64


@pytest.fixture
def leaky_tool():
    name = "fake_leaky"

    async def _execute(args, ctx):
        return ToolResult.ok({"stdout": f"OPENROUTER_API_KEY={LONG_KEY}", "exit_code": 0})

    REGISTRY[name] = Tool(name=name, description="", schema={}, execute=_execute, category="shell")
    yield name
    REGISTRY.pop(name, None)


@pytest.fixture
def session_message():
    """Reale Session + Message — tool_calls.message_id ist FK-gebunden."""
    init_db()
    s = sessions_db.create(agent_id="test-agent-001", user_id="admin")
    m = messages_db.append(s.id, "assistant", "tool call")
    ctx = ToolContext(session_id=s.id, agent_id="test-agent-001", user_id="admin", workspace=Path("/tmp"))
    return ctx, m.id


def test_execute_tool_schwaerzt_secret_im_rueckgabewert(leaky_tool, session_message, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", LONG_KEY)
    ctx, message_id = session_message
    tool_use = {"name": leaky_tool, "input": {}, "id": "tu1"}

    result, _record_id, _ms = asyncio.run(
        execute_tool(tool_use, [leaky_tool], ctx, message_id)
    )

    assert LONG_KEY not in result.output["stdout"]
    assert "[REDACTED]" in result.output["stdout"]
    assert result.output["exit_code"] == 0


def test_execute_tool_schwaerzt_secret_in_db_record(leaky_tool, session_message, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", LONG_KEY)
    ctx, message_id = session_message
    tool_use = {"name": leaky_tool, "input": {}, "id": "tu2"}

    _result, record_id, _ms = asyncio.run(
        execute_tool(tool_use, [leaky_tool], ctx, message_id)
    )

    with db() as conn:
        row = conn.execute("SELECT result FROM tool_calls WHERE id = ?", (record_id,)).fetchone()
    assert LONG_KEY not in row["result"]
