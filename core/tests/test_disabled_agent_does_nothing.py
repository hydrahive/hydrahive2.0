"""Ein deaktivierter Agent tut nichts mehr (Task fbccb7a2).

Verdacht aus der Discord-Doku: bestehende Sessions und Intervalle liefen
weiter. Tatsächlich prüft runner.run den Status; alle Wege (Chat, Intervall,
Kanal) laufen darüber. Dieser Test hält das fest.
"""
from __future__ import annotations

import asyncio

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner
from hydrahive.runner.events import Error


def test_runner_refuses_disabled_agent(setup_test_env, monkeypatch):
    init_db()
    called: list = []

    async def boom(**kwargs):  # darf nie erreicht werden
        called.append(1)
        yield None

    monkeypatch.setattr(runner, "stream_llm_call", boom)
    agent = agent_config.get("test-agent-001")
    monkeypatch.setattr(agent_config, "get", lambda _id: {**agent, "status": "disabled"})
    sid = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="deaktiviert").id

    async def drain():
        return [ev async for ev in runner.run(sid, "Hallo")]

    events = asyncio.run(drain())
    assert any(isinstance(e, Error) and "deaktiviert" in e.message for e in events)
    assert called == []
