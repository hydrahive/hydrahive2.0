"""ask_agent: Briefing-Pflicht – Ziel und Lieferung (Plan E6 T1+T2, Spec agent-templates.md Kap. 9)."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.agents import config as agent_config
from hydrahive.tools import ToolContext, ask_agent
from hydrahive.tools._ask_agent_prepare import build_briefing, missing_briefing


@pytest.fixture
def target(client):
    a = agent_config.create(agent_type="specialist", name="Briefing Ziel", llm_model="m", owner="testuser",
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
    return asyncio.run(ask_agent._execute({"task": "Prüfe den Login", "wait": True, **args}, ctx))


def test_ohne_ziel_und_lieferung_abgelehnt(target, posted, tmp_path):
    res = _run({"agent_id": target["id"]}, tmp_path)
    assert res.success is False and "goal" in res.error and "deliverable" in res.error
    assert posted == []


def test_nur_ziel_reicht_nicht(target, posted, tmp_path):
    res = _run({"agent_id": target["id"], "goal": "Login-Fehler finden"}, tmp_path)
    assert res.success is False and "deliverable" in res.error and posted == []


def test_mit_briefing_ausgefuehrt_und_block_im_auftrag(target, posted, tmp_path):
    res = _run({"agent_id": target["id"], "goal": "Ursache des 500ers beim Login finden",
                "known": "Tritt seit Update auf, Log zeigt KeyError", "deliverable": "Ursache + Fix-Vorschlag mit Datei:Zeile",
                "files": ["core/src/hydrahive/api/auth.py"]}, tmp_path)
    assert res.success is True, res.error
    desc = posted[0].task.description
    assert desc.startswith("Prüfe den Login")
    assert "## Ziel\nUrsache des 500ers beim Login finden" in desc
    assert "## Bekannt\nTritt seit Update auf" in desc
    assert "## Liefern\nUrsache + Fix-Vorschlag" in desc
    assert {"path": "core/src/hydrahive/api/auth.py"} in posted[0].context.files


def test_cancel_und_fortsetzen_brauchen_kein_briefing():
    assert missing_briefing({"cancel": "abc12345"}) == []
    assert missing_briefing({"resume_token": "tok_12345678"}) == []
    assert missing_briefing({"goal": "x", "deliverable": "y"}) == []
    assert missing_briefing({"goal": "  "}) == ["goal", "deliverable"]


def test_block_ohne_bekannt():
    out = build_briefing("T", {"goal": "Z", "deliverable": "L"})
    assert out == "T\n\n## Ziel\nZ\n\n## Liefern\nL"
