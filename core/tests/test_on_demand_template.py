"""Spezialisten „auf Abruf“ (z. B. Security) nur mit task_type review und Begründung (Plan E6 T5)."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.agents import config as agent_config
from hydrahive.tools import ToolContext, ask_agent


@pytest.fixture
def security(client):
    a = agent_config.create(agent_type="specialist", name="Security Abruf", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1024, thinking_budget=0, template="security")
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
        fut.set_result(State(agent_id="x", task=TaskBlock(type="review", description="ok", status="done")))
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(ask_agent, "post_state", fake_post_state)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    return calls


def _run(args, tmp_path):
    ctx = ToolContext(session_id="s", agent_id="test-agent-user", user_id="testuser", workspace=tmp_path)
    return asyncio.run(ask_agent._execute({"task": "Prüfe die neue Route", "goal": "Lücken finden",
                                           "deliverable": "Befunde mit Datei:Zeile", "wait": True, **args}, ctx))


def test_security_template_ist_auf_abruf():
    from hydrahive.agents import templates as tpl
    assert tpl.get("security")["on_demand"] is True


def test_ohne_review_abgelehnt_mit_hinweis(security, posted, tmp_path):
    res = _run({"agent_id": security["id"], "task_type": "feature"}, tmp_path)
    assert res.success is False and "auf Abruf" in res.error and "review" in res.error
    assert posted == []


def test_review_ohne_begruendung_abgelehnt(security, posted, tmp_path):
    res = _run({"agent_id": security["id"], "task_type": "review"}, tmp_path)
    assert res.success is False and "on_demand_reason" in res.error and posted == []


def test_review_mit_begruendung_ausgefuehrt(security, posted, tmp_path):
    res = _run({"agent_id": security["id"], "task_type": "review",
                "on_demand_reason": "Neue Auth-Route mit Token-Prüfung"}, tmp_path)
    assert res.success is True, res.error
    assert any("Auf Abruf: Neue Auth-Route" in e for e in posted[0].context.errors)


def test_normale_spezialisten_unberuehrt(client, posted, tmp_path):
    a = agent_config.create(agent_type="specialist", name="Normal", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1024, thinking_budget=0, template="backend")
    try:
        assert _run({"agent_id": a["id"]}, tmp_path).success is True
    finally:
        agent_config.delete(a["id"])
