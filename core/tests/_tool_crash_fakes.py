"""Gemeinsame Test-Helfer für Tool-Abstürze (Task ff8644b2)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import REGISTRY
from hydrahive.tools.base import Tool, ToolContext, ToolResult

LONG_KEY = "sk-or-v1-" + "c" * 64


@pytest.fixture
def session_message():
    init_db()
    s = sessions_db.create(agent_id="test-agent-crash", user_id="admin")
    m = messages_db.append(s.id, "assistant", "tool call")
    ctx = ToolContext(session_id=s.id, agent_id="test-agent-crash", user_id="admin", workspace=Path("/tmp"))
    return ctx, m.id


def _register(name, execute):
    REGISTRY[name] = Tool(name=name, description="", schema={}, execute=execute, category="shell")


@pytest.fixture
def crashing_tool():
    name = "fake_crashing"

    async def _execute(args, ctx):
        raise ProcessLookupError(f"kaputt mit {LONG_KEY}")

    _register(name, _execute)
    yield name
    REGISTRY.pop(name, None)


@pytest.fixture
def failing_tool():
    """Normaler Tool-Fehler (kein Absturz): darf NICHT in errors_log landen."""
    name = "fake_failing"

    async def _execute(args, ctx):
        return ToolResult.fail("Datei nicht gefunden")

    _register(name, _execute)
    yield name
    REGISTRY.pop(name, None)


def _run(tool, ctx, message_id, tu_id="tu1"):
    return asyncio.run(execute_tool({"name": tool, "input": {"x": 1}, "id": tu_id}, [tool], ctx, message_id))
