"""Per-Agent Secret-Redaction: ein Buddy darf sein eigenes Postfach-Passwort
nicht im Tool-Output leaken (z.B. `cat config.json`).

secret_values() (env + LLM-Config) kennt per-Buddy-Passwörter nicht — die liegen
in der Agent-tool_config. agent_secret_values(agent_id) zieht sie nach; der
dispatcher mischt sie an der Schwärz-Engstelle dazu.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import REGISTRY
from hydrahive.tools.base import Tool, ToolContext, ToolResult

MODEL = "claude-3-7-sonnet-20250219"
LONG_PW = "mailpw-" + "z" * 20   # >= MIN_SECRET_LEN


def _mail_agent(password=LONG_PW):
    a = agent_config.create(agent_type="master", name="secbuddy", llm_model=MODEL,
                            owner="admin", temperature=0.7, max_tokens=1000, thinking_budget=0)
    agent_config.update(a["id"], tool_config={
        "smtp": {"host": "h", "from": "a@b", "user": "u", "password": password}})
    return a["id"]


def test_agent_secret_values_returns_mail_password(client):
    from hydrahive.credentials import redaction
    aid = _mail_agent()
    try:
        assert LONG_PW in redaction.agent_secret_values(aid)
    finally:
        agent_config.delete(aid)


def test_agent_secret_values_empty_for_unknown(client):
    from hydrahive.credentials import redaction
    assert redaction.agent_secret_values("does-not-exist") == set()
    assert redaction.agent_secret_values("") == set()


def test_dispatcher_redacts_per_agent_mail_password(client):
    from hydrahive.db import init_db
    init_db()
    aid = _mail_agent()
    name = "fake_leaky_mail"

    async def _execute(args, ctx):
        return ToolResult.ok({"stdout": f"password={LONG_PW}", "exit_code": 0})

    REGISTRY[name] = Tool(name=name, description="", schema={}, execute=_execute, category="shell")
    try:
        s = sessions_db.create(agent_id=aid, user_id="admin")
        m = messages_db.append(s.id, "assistant", "tool call")
        ctx = ToolContext(session_id=s.id, agent_id=aid, user_id="admin", workspace=Path("/tmp"))

        result, _rid, _ms = asyncio.run(
            execute_tool({"name": name, "input": {}, "id": "tu1"}, [name], ctx, m.id))

        assert LONG_PW not in result.output["stdout"]
        assert "[REDACTED]" in result.output["stdout"]
    finally:
        REGISTRY.pop(name, None)
        agent_config.delete(aid)
