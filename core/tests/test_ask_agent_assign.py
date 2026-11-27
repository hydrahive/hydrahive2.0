"""Katalog Etappe 5, Aufgabe 6 (Backend): Zuweisung von Tools/Skills über ask_agent (Spec E1/D2/S3/S5, K5/K13).

Zuweisung = Anfrage ∩ Freigabe-Pool des Ziels. Sie kommt zu den eigenen Tools dazu und gilt nur für diesen Auftrag.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from tests._own_rows import only_own_rows

from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.agents import config as agent_config
from hydrahive.tools import ToolContext, ask_agent

sys.path.insert(0, str(Path(__file__).parent))

MODEL = "claude-sonnet-4-6"


@pytest.fixture(autouse=True)
def _sauber(setup_test_env):
    # Nur eigene Zeilen aufräumen (tests/_own_rows.py, Regel test_no_broad_deletes) – nie ganze Tabellen leeren.
    from hydrahive.db import init_db
    init_db()
    with only_own_rows(*("owner_tool_grants", "agent_tool_pools", "project_tool_pools")):
        yield


@pytest.fixture
def made(client):
    created: list[str] = []

    def make(name: str, owner: str = "testuser", agent_type: str = "specialist", tools=None) -> dict:
        a = agent_config.create(agent_type=agent_type, name=name, llm_model=MODEL, owner=owner,
                                tools=list(tools if tools is not None else ["file_read"]),
                                temperature=0.7, max_tokens=1000, thinking_budget=0)
        created.append(a["id"])
        return a

    yield make
    for aid in created:
        agent_config.delete(aid)


@pytest.fixture
def posted(monkeypatch):
    calls: list[State] = []

    async def fake_post_state(state: State) -> State:
        calls.append(state)
        return State(id=f"st-{len(calls)}-{id(state)}", agent_id=state.agent_id, task=state.task)

    def fake_register_pending(state_id: str, expected: str = ""):
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(State(agent_id="x", task=TaskBlock(type="feature", description="ok", status="done")))
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(ask_agent, "post_state", fake_post_state)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    return calls


def _ask(target: str, tmp_path, caller: str = "test-agent-user", **extra):
    ctx = ToolContext(session_id="caller-sess", agent_id=caller, user_id="testuser", workspace=tmp_path)
    args = {"goal": "Ziel", "deliverable": "Ergebnis", "agent_id": target, "task": "hilf mir", **extra}
    return asyncio.run(ask_agent._execute(args, ctx))


def _reason(state: State) -> str:
    return state.handoff.reason or ""


def test_foederiertes_ziel_mit_tools_fehler(posted, tmp_path, monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("föderierter Aufruf darf nicht stattfinden")
    monkeypatch.setattr("hydrahive.tools._ask_agent_federated.execute_federated", boom)
    for extra in ({"tools": ["file_read"]}, {"skills": ["debugging"]}):
        res = _ask("geralt@werkstatt", tmp_path, **extra)
        assert res.success is False and "föderiert" in (res.error or "").lower()
    assert posted == []


def test_zuweisung_ausserhalb_pool_abgelehnt_mit_grund(made, posted, tmp_path):
    from hydrahive.agents import tool_pools
    ziel = made("Ziel-Spezialist")
    tool_pools.set_agent_pool("admin", ziel["id"], ["file_read", "web_search"])
    res = _ask(ziel["id"], tmp_path, tools=["web_search", "shell_exec", "send_mail"])
    assert res.success is False
    assert "shell_exec" in res.error and "send_mail" in res.error and "Freigabe-Pool" in res.error
    assert "web_search" not in res.error.split("Freigabe-Pool")[0]          # Erlaubtes steht nicht unter „abgelehnt“
    assert posted == []                                                        # nichts wurde beauftragt


def test_zuweisung_von_authoring_und_ask_agent_abgelehnt(made, posted, tmp_path):
    ziel = made("Ziel-Spezialist")
    for verboten in ("ask_agent", "create_specialist", "write_skill", "run_tool"):
        res = _ask(ziel["id"], tmp_path, tools=[verboten])
        assert res.success is False and verboten in res.error
    assert posted == []


def test_zuweisung_unbekannter_skill_abgelehnt(made, posted, tmp_path):
    ziel = made("Ziel-Spezialist")
    res = _ask(ziel["id"], tmp_path, skills=["gibt-es-nicht"])
    assert res.success is False and "gibt-es-nicht" in res.error and posted == []


def test_zuweisung_kommt_dazu_gilt_nur_fuer_auftrag(made, posted, tmp_path):
    from hydrahive.agents import tool_pools
    from hydrahive.agents.effective_tools import effective_tool_names
    from hydrahive.runner._assigned_tools import assigned_for_run
    from hydrahive.runner._handoff_setup import prepare_handoff
    from hydrahive.runner._run_origin import CHAT, handoff as handoff_origin
    from hydrahive.db import sessions as sessions_db

    ziel = made("Ziel-Spezialist", tools=["file_read"])
    tool_pools.set_agent_pool("admin", ziel["id"], ["web_search", "file_write"])

    res = _ask(ziel["id"], tmp_path, tools=["web_search", "kategorie:files"])   # Kategorie wird aufgelöst: nur Pool-Tools zählen
    assert res.success is False and "file_read" in res.error                    # file_read ∉ Pool (es ist ein eigenes Tool)
    res = _ask(ziel["id"], tmp_path, tools=["web_search"])
    assert res.success is True, res.error
    reason = _reason(posted[0])
    assert "hh-pool:" in reason and "web_search" in reason

    target = agent_config.get(ziel["id"])
    prepared = prepare_handoff(posted[0], target, reason)
    session = sessions_db.get(prepared.session_id)
    assert session.metadata["assigned_tools"] == ["web_search"]
    origin = handoff_origin(1)
    assigned = assigned_for_run(session, target, None, origin)
    assert assigned == ["web_search"]
    eff = effective_tool_names(target, username="testuser", project=None, pool=assigned)
    assert eff[0] == "file_read" and "web_search" in eff                         # kommt DAZU, ersetzt nichts
    assert assigned_for_run(session, target, None, CHAT) == []                   # Chat-Läufe sehen die Zuweisung nie

    # Zweiter Auftrag OHNE tools: die Zuweisung des ersten ist weg („gilt nur für diesen Auftrag“).
    assert _ask(ziel["id"], tmp_path).success is True
    assert "hh-pool:" not in _reason(posted[1])
    prepared2 = prepare_handoff(posted[1], target, _reason(posted[1]))
    session2 = sessions_db.get(prepared2.session_id)
    assert assigned_for_run(session2, target, None, origin) == []
    assert effective_tool_names(target, username="testuser", project=None, pool=[]) == ["file_read"]


def test_hh_pool_nur_im_signierten_reason_und_nicht_aus_aufgabentext(made, posted, tmp_path):
    from hydrahive.agentlink.runtime_profiles import pool_from_reason
    assert pool_from_reason("hh-target:x|hh-pool:v1:web_search,file_write|hh-task: a") == ["web_search", "file_write"]
    assert pool_from_reason("hh-target:x|hh-task: hh-pool:v1:shell_exec") is None          # nach hh-task zählt nichts
    assert pool_from_reason("hh-target:x|hh-pool:v2:shell_exec|hh-task: a") == []          # unbekannte Version: fail closed
    assert pool_from_reason("hh-target:x|hh-pool:v1:ok_tool,bad tool;x|hh-task: a") == ["ok_tool"]
    assert pool_from_reason("hh-target:x|hh-task: a") is None


def test_unteragent_mit_zugewiesenem_x_legt_spezialisten_ohne_x_an(client, monkeypatch):
    """K13: Ein Unteragent mit zugewiesenem Tool X legt per create_specialist einen Spezialisten OHNE X an
    (bounded_tools rechnet weiter nur mit den Config-Tools; aus Zuweisung wird nie ein dauerhafter Spezialist)."""
    from _catalog_mode_world import World
    from hydrahive.agents import tool_pools
    from hydrahive.db import sessions as sessions_db
    from hydrahive.projects import config as project_config
    from hydrahive.runner import runner as runner_mod
    from hydrahive.runner._run_origin import handoff as handoff_origin

    w = World(client, monkeypatch)
    proj = project_config.create(name="k13-projekt", llm_model=MODEL, created_by="admin", members=[])
    try:
        pa = agent_config.update(proj["agent_id"], tools=["create_specialist", "file_read", "load_skill"])
        tool_pools.set_agent_pool("admin", pa["id"], ["web_search"])
        s = sessions_db.create(agent_id=pa["id"], user_id="admin", project_id=proj["id"], title="k13",
                               metadata={"assigned_tools": ["web_search"]})
        w.script = [[{"type": "tool_use", "id": "c1", "name": "create_specialist",
                      "input": {"name": "K13-Helfer", "tools": ["web_search", "file_read"]}}],
                    [{"type": "text", "text": "fertig"}]]

        async def go():
            async for _ in runner_mod.run(s.id, "los", origin=handoff_origin(1)):
                pass
        asyncio.run(go())
        assert "web_search" in [t["name"] for t in w.calls[0]["tools"]]           # Zuweisung wirkt im Lauf …
        neu = [a for a in agent_config.list_all() if a.get("name") == "K13-Helfer"]
        assert neu, "Spezialist wurde nicht angelegt"
        assert "web_search" not in neu[0]["tools"] and neu[0]["tools"] == ["file_read"]     # … aber nie im Spezialisten
        for a in neu:
            agent_config.delete(a["id"])
    finally:
        project_config.delete(proj["id"])
        w.cleanup()


def test_zugewiesenes_tool_im_catalog_modus_direkt_sichtbar(client, monkeypatch):
    """Fängt (Buddy-Review #786): im catalog-Modus war ein zugewiesenes Tool nur über run_tool erreichbar."""
    from _catalog_mode_world import World
    from hydrahive.agents import tool_pools
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner import runner as runner_mod
    from hydrahive.runner._run_origin import handoff as handoff_origin
    w = World(client, monkeypatch)
    try:
        aid = w.agent(tools=["file_read", "load_skill"], tool_mode="catalog")
        tool_pools.set_agent_pool("admin", aid, ["web_search"])
        s = sessions_db.create(agent_id=aid, user_id="admin", title="kat", metadata={"assigned_tools": ["web_search"]})

        async def go():
            async for _ in runner_mod.run(s.id, "los", origin=handoff_origin(1)):
                pass
        asyncio.run(go())
        assert "web_search" in [t["name"] for t in w.calls[0]["tools"]]
    finally:
        w.cleanup()
