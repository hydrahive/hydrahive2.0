"""Eingehende Handoffs werden beim Dispatch in der Registry sichtbar und beim
Server-Stopp gezielt beendet (Spec delegation-reliability.md 3.1), damit der
Checkpoint-Pfad in handoff_receiver._run_and_reply (3.2) überhaupt eine Chance
bekommt zu laufen, statt vom Event-Loop fire-and-forget abgeschnitten zu werden."""
from __future__ import annotations

import asyncio

from hydrahive.agentlink.protocol import Handoff, State, TaskBlock
from hydrahive.api import lifespan
from hydrahive.agentlink.protocol import WSEvent
from hydrahive.runner import handoff_tasks


def _incoming_state(sid: str) -> State:
    return State(
        id=sid, agent_id="caller",
        task=TaskBlock(type="feature", description="x"),
        handoff=Handoff(to_agent="ziel", reason="hh-target:ziel|hh-task: x"),
    )


def test_dispatch_registriert_den_handoff_task(monkeypatch):
    handoff_tasks.clear_for_test()
    state = _incoming_state("st-reg-1")

    started = asyncio.Event()

    async def _fake_handle(event):
        started.set()
        await asyncio.sleep(5)

    monkeypatch.setattr(lifespan.handoff_receiver, "handle", _fake_handle)

    async def _get_state(_sid):
        return state

    async def go():
        await lifespan.dispatch_agentlink_event(
            WSEvent(type="handoff_received", state_id=state.id),
            get_state=_get_state,
        )
        await started.wait()
        assert handoff_tasks.active_count() == 1
        await handoff_tasks.shutdown(timeout=1.0)
        assert handoff_tasks.active_count() == 0

    asyncio.run(go())


def test_paused_delegation_bleibt_nach_reconcile_on_start_unberuehrt(client):
    """Sobald der CancelledError-Pfad (3.2) eine Delegation auf 'paused' gesetzt hat,
    ist sie beim nächsten Start nicht mehr 'running' — reconcile_on_start() (3.3) greift
    dort also gar nicht mehr zu. Nur echte Abstürze ohne Checkpoint bleiben 'lost'."""
    from hydrahive.db import delegations as delegations_db
    from hydrahive.db import sessions as sessions_db

    sid = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="graceful").id
    d = delegations_db.create(
        session_id=sid, agent_id="a", user_id="admin",
        target_agent_id="t", target_name="T", task="x",
        state_id="st-graceful-1", depth=1, timeout_seconds=60,
    )
    # Simuliert, was record_delegation_result beim Checkpoint-Pfad tut:
    delegations_db.complete_if_running(d["id"], "paused", "Pausiert: Server-Neustart.")

    lost = delegations_db.reconcile_on_start()

    row = delegations_db.get_by_state("st-graceful-1")
    assert row["status"] == "paused"  # NICHT von reconcile_on_start überschrieben
    assert lost == 0 or row["status"] != "lost"
