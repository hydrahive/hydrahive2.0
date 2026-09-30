"""Tool-Abstürze landen in errors_log (Task ff8644b2).

Bisher schrieben Tool-, MCP- und Plugin-Abstürze nur ins Journal. Die Ursache
von 184 shell_exec-Abstürzen blieb dadurch monatelang unentdeckt.

Vereinbart (Till 30.09.2026, Variante A):
- Jeder Absturz schreibt einen Eintrag in errors_log (Quelle, Tool, Traceback).
- Der Traceback wird mit denselben Secret-Werten geschwärzt wie der Tool-Output.
- Die Dashboard-Kachel „Heute Fehler“ zählt einen Absturz nur EINMAL
  (er steht schon als fehlgeschlagener tool_call drin).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.db import errors_log
from hydrahive.db.connection import db
from hydrahive.runner.dispatcher import execute_tool
from tests._tool_crash_fakes import LONG_KEY, _run

pytest_plugins = ["tests._tool_crash_fakes"]

def test_tool_absturz_landet_in_errors_log(crashing_tool, session_message, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", LONG_KEY)
    ctx, message_id = session_message
    result, record_id, _ = _run(crashing_tool, ctx, message_id)

    assert not result.success and result.error.startswith("Tool-Crash: ProcessLookupError")
    rows = errors_log.for_session(ctx.session_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["source"] == "tool.crash"
    assert row["error_type"] == "ProcessLookupError"
    assert row["agent_id"] == "test-agent-crash" and row["user_id"] == "admin"
    assert "ProcessLookupError" in row["traceback"] and "_execute" in row["traceback"]
    assert f'"tool": "{crashing_tool}"' in row["context"]
    assert record_id in row["context"], "Verweis auf den tool_calls-Eintrag fehlt"


def test_traceback_und_meldung_sind_geschwaerzt(crashing_tool, session_message, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", LONG_KEY)
    ctx, message_id = session_message
    _run(crashing_tool, ctx, message_id)

    with db() as conn:
        row = conn.execute("SELECT * FROM errors_log WHERE session_id = ?", (ctx.session_id,)).fetchone()
    for col in ("error_message", "traceback", "context"):
        assert LONG_KEY not in (row[col] or ""), f"Secret in errors_log.{col}"
    assert "[REDACTED]" in row["traceback"]


def test_normaler_tool_fehler_landet_nicht_in_errors_log(failing_tool, session_message):
    ctx, message_id = session_message
    result, _, _ = _run(failing_tool, ctx, message_id)
    assert not result.success
    assert errors_log.for_session(ctx.session_id) == []


def test_plugin_crash_error_type_wird_erkannt():
    from hydrahive.runner.dispatcher import _extract_error_type
    assert _extract_error_type("Plugin-Crash: KeyError: 'x'") == "KeyError"
    assert _extract_error_type("MCP-Crash: TimeoutError: weg") == "TimeoutError"
    assert _extract_error_type("Tool-Crash: ValueError: kaputt") == "ValueError"
    assert _extract_error_type("Datei nicht gefunden") is None


def test_plugin_absturz_landet_in_errors_log(session_message, monkeypatch):
    from hydrahive.plugins import tool_bridge as plugin_bridge

    ctx, message_id = session_message
    name = f"{plugin_bridge.PREFIX}fakeplug__boom"

    async def _fake_call(qualified_name, args, tool_ctx):
        return plugin_bridge._crash_result(qualified_name, RuntimeError("plugin kaputt"), tool_ctx)

    monkeypatch.setattr(plugin_bridge, "call", _fake_call)
    result, _, _ = asyncio.run(execute_tool({"name": name, "input": {}, "id": "tp"}, [name], ctx, message_id))
    assert result.error.startswith("Plugin-Crash: RuntimeError")
    rows = errors_log.for_session(ctx.session_id)
    assert [r["source"] for r in rows] == ["plugin.crash"]
    with db() as conn:
        et = conn.execute("SELECT error_type FROM tool_calls WHERE session_id = ?", (ctx.session_id,)).fetchone()[0]
    assert et == "RuntimeError"


def test_mcp_absturz_landet_in_errors_log(session_message, monkeypatch):
    from hydrahive.mcp import tool_bridge as mcp_bridge

    ctx, message_id = session_message
    name = f"{mcp_bridge.PREFIX}srv__boom"

    async def _boom(tool_name, args):
        raise ConnectionError("mcp weg")

    monkeypatch.setattr(mcp_bridge, "call", _boom)
    result, _, _ = asyncio.run(execute_tool({"name": name, "input": {}, "id": "tm"}, [name], ctx, message_id))
    assert result.error.startswith("MCP-Crash: ConnectionError")
    assert [r["source"] for r in errors_log.for_session(ctx.session_id)] == ["mcp.crash"]


@pytest.mark.parametrize("target", ["hydrahive.db.errors_log.db", "hydrahive.runner._crash_log.crash_secrets"])
def test_errors_log_ausfall_bricht_den_toollauf_nicht(target, crashing_tool, session_message, monkeypatch):
    """Weder ein DB-Ausfall noch ein Fehler beim Schwärzen darf den Toollauf abbrechen."""
    ctx, message_id = session_message

    def _kaputt(*a, **kw):
        raise RuntimeError("kaputt")

    monkeypatch.setattr(target, _kaputt)
    result, _, _ = _run(crashing_tool, ctx, message_id)
    assert not result.success and result.error.startswith("Tool-Crash:")
