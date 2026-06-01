"""Tool-Authorization-Gate im Dispatcher (Issue #205, kritischer Pfad).

execute_tool muss ein nicht erlaubtes Tool ablehnen (ToolResult.fail) und den
Versuch trotzdem als tool_calls-Eintrag mit status='error' persistieren.
"""
from __future__ import annotations

import asyncio

from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import ToolContext


def _ctx(session_id, tmp_path):
    return ToolContext(session_id=session_id, agent_id="a1", user_id="u1", workspace=tmp_path)


def _status(record_id: str) -> str:
    with db() as conn:
        row = conn.execute("SELECT status FROM tool_calls WHERE id = ?", (record_id,)).fetchone()
    return row[0] if row else ""


def test_disallowed_tool_rejected_and_recorded(client, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    tool_use = {"id": "tu1", "name": "shell_exec", "input": {"cmd": "id"}}

    async def body():
        return await execute_tool(tool_use, ["read_file"], _ctx(s.id, tmp_path), msg.id)

    result, rec_id, _ = asyncio.run(body())

    assert result.success is False
    assert "nicht erlaubt" in (result.error or "")
    assert _status(rec_id) == "error", "abgelehnter Tool-Call muss als error persistiert werden"


def test_unknown_tool_in_allowlist_reports_not_found(client, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    tool_use = {"id": "tu2", "name": "ghost_tool", "input": {}}

    async def body():
        return await execute_tool(tool_use, ["ghost_tool"], _ctx(s.id, tmp_path), msg.id)

    result, _, _ = asyncio.run(body())

    assert result.success is False
    assert "weder lokal noch MCP" in (result.error or "")
