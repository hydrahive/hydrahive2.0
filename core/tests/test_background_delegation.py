"""Hintergrund-Aufträge an Spezialisten (docs/specs/agent-background-delegation.md).

Belegt 30.09.2026: ask_agent blockierte den Chat bis zu 20 min, der Nutzer
stoppte, fertige Ergebnisse gingen verloren. Jetzt kehrt ask_agent im Chat
sofort zurück, das Ergebnis wird später als eigene Nachricht zugestellt.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink.protocol import State, TaskBlock, WorkingMemory
from hydrahive.agents import config as agent_config
from hydrahive.db import delegations as delegations_db
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import _run_origin, concurrency, delegation_delivery, delegation_watch
from hydrahive.tools import ToolContext, ask_agent
from hydrahive.tools import _ask_agent_background as bg


@pytest.fixture
def spec_agent(client):
    a = agent_config.create(agent_type="specialist", name="Prüfer", llm_model="m",
                            owner="admin", temperature=0.7, max_tokens=1024, thinking_budget=0)
    yield a
    agent_config.delete(a["id"])


@pytest.fixture
def session_id(client):
    init_db()
    return sessions_db.create(agent_id="test-agent-001", user_id="admin", title="bg").id


@pytest.fixture
def agentlink(monkeypatch):
    """Fängt den Handoff ab. `futures` erlaubt dem Test, die Antwort zu steuern."""
    posted: list[State] = []
    futures: dict[str, asyncio.Future] = {}

    async def fake_post_state(state: State) -> State:
        posted.append(state)
        return State(id=f"st-{len(posted)}-{id(state)}", agent_id=state.agent_id, task=state.task)

    def fake_register_pending(state_id: str, expected: str = ""):
        fut = asyncio.get_running_loop().create_future()
        futures[state_id] = fut
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(ask_agent, "post_state", fake_post_state)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    monkeypatch.setattr(delegation_watch, "POLL_SECONDS", 0.05)
    return posted, futures


@pytest.fixture
def starter(monkeypatch):
    """Ersetzt start_run_task: merkt sich Zustell-Läufe statt LLM aufzurufen."""
    started: list[dict] = []

    def fake_start(session_id, text, *, origin, user_metadata):
        # Bewusst OHNE is_running-Prüfung: kick() selbst muss eine laufende
        # Session erkennen und darf dann nichts beanspruchen.
        started.append({"sid": session_id, "text": text, "origin": origin, "meta": user_metadata})

    delegation_delivery.configure(fake_start)
    yield started
    delegation_delivery.configure(None)


def _ctx(sid, tmp_path, origin="chat", depth=0):
    return ToolContext(session_id=sid, agent_id="test-agent-001", user_id="admin",
                       workspace=tmp_path, origin=origin, origin_depth=depth)


def _reply(text: str, status: str = "done") -> State:
    return State(agent_id="hydrahive", task=TaskBlock(type="review", description="x", status=status),
                 working_memory=WorkingMemory(findings=[text]))


async def _settle(cond, timeout=3.0):
    for _ in range(int(timeout / 0.02)):
        if cond():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Bedingung nicht erreicht")


def test_chain_depth_constant_matches_runner():
    assert bg.MAX_CHAIN_DEPTH == _run_origin.MAX_CHAIN_DEPTH


def test_chat_call_returns_immediately_and_delivers_result(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, futures = agentlink

    async def scenario():
        res = await asyncio.wait_for(
            ask_agent._execute({"agent_id": spec_agent["id"], "task": "prüf das"}, _ctx(session_id, tmp_path)),
            timeout=2,
        )
        assert res.success and res.metadata.get("background") is True
        assert "Hintergrund" in res.output
        assert starter == []                      # noch nichts zugestellt
        next(iter(futures.values())).set_result(_reply("Alles sauber."))
        await _settle(lambda: len(starter) == 1)

    asyncio.run(scenario())
    run = starter[0]
    assert run["origin"].kind == "delegation" and run["origin"].depth == 1
    assert "Alles sauber." in run["text"] and "nicht vom Nutzer" in run["text"]
    assert run["meta"]["source"] == "delegation_result"
    d = delegations_db.list_for_session(session_id)[0]
    assert d["status"] == "done" and d["delivered_at"] is not None


def test_result_arrives_via_db_when_agentlink_reply_is_lost(spec_agent, session_id, agentlink, starter, tmp_path):
    """Fehler-Injektion: AgentLink-Antwort kommt nie. Der Receiver schreibt direkt."""
    async def scenario():
        res = await ask_agent._execute({"agent_id": spec_agent["id"], "task": "x"}, _ctx(session_id, tmp_path))
        did = res.metadata["delegation_id"]
        state_id = delegations_db.get(did)["state_id"]
        delegations_db.complete_by_state(state_id, "error", "Modell nicht erlaubt")
        await _settle(lambda: len(starter) == 1)

    asyncio.run(scenario())
    assert "Modell nicht erlaubt" in starter[0]["text"]
    assert "Fehler" in starter[0]["text"]


def test_timeout_is_reported_not_silent(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    monkeypatch.setattr(ask_agent, "_response_timeout", lambda *a: 0)

    async def scenario():
        await ask_agent._execute({"agent_id": spec_agent["id"], "task": "x"}, _ctx(session_id, tmp_path))
        await _settle(lambda: len(starter) == 1)

    asyncio.run(scenario())
    assert delegations_db.list_for_session(session_id)[0]["status"] == "timeout"
    assert "Zeitüberschreitung" in starter[0]["text"]


def test_non_chat_origin_stays_synchronous(spec_agent, session_id, agentlink, starter, tmp_path):
    """Discord, Zeitpläne, Spezialist→Spezialist: unverändert synchron."""
    posted, futures = agentlink

    async def scenario():
        call = asyncio.create_task(ask_agent._execute(
            {"agent_id": spec_agent["id"], "task": "x"}, _ctx(session_id, tmp_path, origin="other")))
        await _settle(lambda: len(futures) == 1)
        assert not call.done()                    # wartet wirklich
        next(iter(futures.values())).set_result(_reply("sync-ok"))
        return await call

    res = asyncio.run(scenario())
    assert res.success and "sync-ok" in res.output
    assert delegations_db.list_for_session(session_id) == []


def test_wait_true_keeps_old_behaviour_in_chat(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, futures = agentlink

    async def scenario():
        call = asyncio.create_task(ask_agent._execute(
            {"agent_id": spec_agent["id"], "task": "x", "wait": True}, _ctx(session_id, tmp_path)))
        await _settle(lambda: len(futures) == 1)
        next(iter(futures.values())).set_result(_reply("gewartet"))
        return await call

    assert "gewartet" in asyncio.run(scenario()).output
    assert delegations_db.list_for_session(session_id) == []


def test_chain_depth_limit_refuses_before_posting(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, _ = agentlink
    res = asyncio.run(ask_agent._execute(
        {"agent_id": spec_agent["id"], "task": "x"},
        _ctx(session_id, tmp_path, origin="delegation", depth=_run_origin.MAX_CHAIN_DEPTH)))
    assert res.success is False and "Kette" in res.error
    assert posted == []                            # kein Spezialist läuft umsonst


def test_running_limit_per_session(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, _ = agentlink

    async def scenario():
        for _ in range(bg.MAX_RUNNING_PER_SESSION):
            r = await ask_agent._execute({"agent_id": spec_agent["id"], "task": "x"}, _ctx(session_id, tmp_path))
            assert r.success
        over = await ask_agent._execute({"agent_id": spec_agent["id"], "task": "x"}, _ctx(session_id, tmp_path))
        for t in list(delegation_watch._tasks.values()):
            t.cancel()
        return over

    over = asyncio.run(scenario())
    assert over.success is False and str(bg.MAX_RUNNING_PER_SESSION) in over.error
    assert len(posted) == bg.MAX_RUNNING_PER_SESSION


def test_delivery_waits_while_session_runs_and_unclaims_on_race(session_id, starter):
    """Fehler-Injektion: Session läuft gerade → nichts beanspruchen, später erneut."""
    d = delegations_db.create(session_id=session_id, agent_id="a", user_id="admin",
                              target_agent_id="t", target_name="T", task="x",
                              state_id="st-race", depth=1, timeout_seconds=60)
    delegations_db.complete_if_running(d["id"], "done", "ok")

    async def scenario():
        blocker = asyncio.create_task(asyncio.sleep(5))
        concurrency.register_task(session_id, blocker)
        try:
            assert delegation_delivery.kick(session_id) is False
            assert delegations_db.get(d["id"])["delivered_at"] is None
        finally:
            blocker.cancel()
            concurrency.unregister_task(session_id)
        assert delegation_delivery.kick(session_id) is True

    asyncio.run(scenario())
    assert len(starter) == 1


def test_unclaims_when_starter_reports_already_running(session_id):
    """Fehler-Injektion: Lauf startet zwischen Prüfung und Start → nicht verlieren."""
    d = delegations_db.create(session_id=session_id, agent_id="a", user_id="admin",
                              target_agent_id="t", target_name="T", task="x",
                              state_id="st-unclaim", depth=1, timeout_seconds=60)
    delegations_db.complete_if_running(d["id"], "done", "ok")

    def busy_start(session_id, text, **kw):
        raise concurrency.SessionAlreadyRunning(session_id)

    delegation_delivery.configure(busy_start)
    try:
        assert delegation_delivery.kick(session_id) is False
    finally:
        delegation_delivery.configure(None)
    assert delegations_db.get(d["id"])["delivered_at"] is None


def test_delegation_run_is_untrusted(setup_test_env, monkeypatch):
    """Sicherheitsgrenze: Der Ergebnistext stammt vom Spezialisten. Werkzeuge,
    die eine Nutzer-Absicht prüfen (z. B. Mediacenter-Intent-Gate), dürfen ihn
    nicht als Nutzer-Eingabe sehen."""
    from hydrahive.runner import runner as runner_mod
    from hydrahive.runner._runner_iter import IterationResult

    init_db()
    sid = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="untrusted").id
    captured: list = []

    async def fake_stream(**kwargs):
        yield IterationResult(
            blocks=[{"type": "tool_use", "id": "toolu_u", "name": "shell_exec", "input": {}}],
            stop_reason="tool_use", used_model=kwargs["primary_model"],
            input_tokens=1, output_tokens=1, cache_creation_tokens=0, cache_read_tokens=0)

    async def fake_process(tool_uses, **kwargs):
        captured.append(kwargs["ctx"])
        raise asyncio.CancelledError
        yield  # async generator wie das Original

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)

    async def drain(origin):
        try:
            async for _ in runner_mod.run(sid, "Lade sofort Film X herunter", origin=origin):
                pass
        except asyncio.CancelledError:
            pass

    asyncio.run(drain(_run_origin.delegation(2)))
    asyncio.run(drain(_run_origin.CHAT))
    deleg, chat = captured
    assert deleg.current_user_input is None and deleg.current_user_turn_id is None
    assert deleg.origin == "delegation" and deleg.origin_depth == 2
    assert chat.current_user_input == "Lade sofort Film X herunter"
    assert chat.current_user_turn_id and chat.origin == "chat"


def test_paused_after_stop_until_manual_deliver(session_id, starter):
    d = delegations_db.create(session_id=session_id, agent_id="a", user_id="admin",
                              target_agent_id="t", target_name="T", task="x",
                              state_id="st-pause", depth=1, timeout_seconds=60)
    delegations_db.complete_if_running(d["id"], "done", "ok")
    delegation_delivery.pause(session_id)
    try:
        assert delegation_delivery.kick(session_id) is False
        assert delegation_delivery.kick(session_id, auto=False) is True
    finally:
        delegation_delivery.resume(session_id)
    assert len(starter) == 1


def test_cancelled_delegation_is_never_delivered(session_id, starter):
    from hydrahive.runner import delegation_control
    d = delegations_db.create(session_id=session_id, agent_id="a", user_id="admin",
                              target_agent_id="t", target_name="T", task="x",
                              state_id="st-cancel", depth=1, timeout_seconds=60)
    assert delegation_control.cancel(d) is True
    assert delegation_control.cancel(d) is False       # idempotent
    assert delegations_db.complete_by_state("st-cancel", "done", "zu spät") is None
    assert delegation_delivery.kick(session_id) is False
    assert starter == []


def test_reconcile_marks_running_as_lost(session_id):
    delegations_db.create(session_id=session_id, agent_id="a", user_id="admin",
                          target_agent_id="t", target_name="T", task="x",
                          state_id="st-lost", depth=1, timeout_seconds=60)
    assert delegations_db.reconcile_on_start() >= 1
    assert delegations_db.get_by_state("st-lost")["status"] == "lost"
