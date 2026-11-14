"""ask_agent: Budget-Überschreitung nur mit Begründung (Plan E4 T2+T3)."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.agentlink.runtime_profiles import profile_from_reason
from hydrahive.agents import config as agent_config
from hydrahive.tools import ToolContext, ask_agent


@pytest.fixture
def target(client):
    a = agent_config.create(agent_type="specialist", name="Overrun Ziel", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1024, thinking_budget=0)
    yield a
    agent_config.delete(a["id"])


@pytest.fixture
def posted(monkeypatch):
    calls: list[State] = []

    async def fake_post_state(state: State) -> State:
        calls.append(state)
        return State(id=f"st-{len(calls)}", agent_id=state.agent_id, task=state.task)

    def fake_register_pending(state_id: str, expected: str = ""):
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(State(agent_id="x", task=TaskBlock(type="feature", description="ok", status="done")))
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(ask_agent, "post_state", fake_post_state)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    return calls


def _run(args: dict, tmp_path):
    ctx = ToolContext(session_id="s", agent_id="test-agent-user", user_id="testuser", workspace=tmp_path)
    return asyncio.run(ask_agent._execute({"task": "prüf alles", "wait": True, **args}, ctx))


def test_overrun_ohne_begruendung_abgelehnt(target, posted, tmp_path):
    res = _run({"agent_id": target["id"], "overrun": True}, tmp_path)
    assert res.success is False and "overrun_reason" in (res.error or "")
    assert posted == []


def test_overrun_mit_begruendung(target, posted, tmp_path):
    res = _run({"agent_id": target["id"], "overrun": True,
                "overrun_reason": "Review über 40 Dateien, Standardbudget reicht nicht"}, tmp_path)
    assert res.success is True, res.error
    assert profile_from_reason(posted[0].handoff.reason) == "overrun"
    assert any("Review über 40 Dateien" in e for e in posted[0].context.errors)


def test_ohne_overrun_unveraendert(target, posted, tmp_path):
    res = _run({"agent_id": target["id"]}, tmp_path)
    assert res.success is True
    assert profile_from_reason(posted[0].handoff.reason) == "standard"
    assert posted[0].context.errors == []


def test_schema_kennt_overrun():
    props = ask_agent.TOOL.schema["properties"]
    assert "overrun" in props and "overrun_reason" in props
