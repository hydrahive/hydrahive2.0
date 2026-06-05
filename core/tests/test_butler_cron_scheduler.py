"""F3 — Butler Cron-Emitter: feuert cron_fired-Flows zeitgesteuert.

Der cron_fired-Trigger hatte bislang keinen Emitter (SPEC-Phase-2-Lücke).
Der Scheduler wertet pro Tick das Fenster (since, now] aus: jede geplante
Zeit feuert genau einmal.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

import hydrahive.butler.scheduler as sched
from hydrahive.butler.models import Flow, Node, NodePosition

UTC = timezone.utc


def _cron_flow(*, owner="alice", cron="* * * * *", schedule_id="", enabled=True, flow_id="f1") -> Flow:
    params = {"cron": cron}
    if schedule_id:
        params["schedule_id"] = schedule_id
    node = Node(id="t1", type="trigger", subtype="cron_fired", position=NodePosition(x=0, y=0), params=params)
    return Flow(flow_id=flow_id, name="TestFlow", owner=owner, enabled=enabled, nodes=[node])


# ---- _due (reine Fenster-Logik) ----

def test_due_taeglich_im_fenster():
    # "0 8 * * *" feuert 08:00; Fenster 07:59→08:01 enthält es
    assert sched._due("0 8 * * *", datetime(2026, 6, 5, 7, 59, tzinfo=UTC), datetime(2026, 6, 5, 8, 1, tzinfo=UTC)) is True


def test_due_taeglich_ausserhalb_fenster():
    assert sched._due("0 8 * * *", datetime(2026, 6, 5, 8, 1, tzinfo=UTC), datetime(2026, 6, 5, 8, 2, tzinfo=UTC)) is False


def test_due_jede_minute_im_fenster():
    assert sched._due("* * * * *", datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC), datetime(2026, 6, 5, 10, 1, 0, tzinfo=UTC)) is True


def test_due_jede_minute_zu_kurzes_fenster():
    # Fenster 10:00:10→10:00:50 enthält keinen Minutenwechsel
    assert sched._due("* * * * *", datetime(2026, 6, 5, 10, 0, 10, tzinfo=UTC), datetime(2026, 6, 5, 10, 0, 50, tzinfo=UTC)) is False


# ---- _cron_trigger ----

def test_cron_trigger_findet_node():
    flow = _cron_flow()
    node = sched._cron_trigger(flow)
    assert node is not None and node.subtype == "cron_fired"


def test_cron_trigger_none_ohne_cron():
    node = Node(id="t1", type="trigger", subtype="webhook_received", position=NodePosition(x=0, y=0), params={})
    flow = Flow(flow_id="f1", name="NoCron", owner="alice", enabled=True, nodes=[node])
    assert sched._cron_trigger(flow) is None


# ---- _tick (Integration: due → dispatch) ----

@pytest.fixture
def capture_dispatch(monkeypatch):
    calls: list = []

    async def fake_dispatch(flow, event, **kw):
        calls.append((flow, event))
        return {"matched": True}

    monkeypatch.setattr(sched.bex, "dispatch", fake_dispatch)
    return calls


async def test_tick_feuert_faellige_flows(monkeypatch, capture_dispatch):
    flow = _cron_flow(cron="* * * * *", schedule_id="daily")
    monkeypatch.setattr(sched.bp, "list_flows", lambda owner=None: [flow])

    fired = await sched._tick(datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC), datetime(2026, 6, 5, 10, 1, 0, tzinfo=UTC))
    assert fired == 1
    assert len(capture_dispatch) == 1
    _, event = capture_dispatch[0]
    assert event.event_type == "cron"
    assert event.owner == "alice"
    assert event.payload.get("schedule_id") == "daily"


async def test_tick_ueberspringt_nicht_faellige(monkeypatch, capture_dispatch):
    flow = _cron_flow(cron="* * * * *")
    monkeypatch.setattr(sched.bp, "list_flows", lambda owner=None: [flow])
    fired = await sched._tick(datetime(2026, 6, 5, 10, 0, 10, tzinfo=UTC), datetime(2026, 6, 5, 10, 0, 50, tzinfo=UTC))
    assert fired == 0
    assert capture_dispatch == []


async def test_tick_ueberspringt_disabled(monkeypatch, capture_dispatch):
    flow = _cron_flow(cron="* * * * *", enabled=False)
    monkeypatch.setattr(sched.bp, "list_flows", lambda owner=None: [flow])
    fired = await sched._tick(datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC), datetime(2026, 6, 5, 10, 1, 0, tzinfo=UTC))
    assert fired == 0
    assert capture_dispatch == []


async def test_tick_ungueltige_expression_kein_crash(monkeypatch, capture_dispatch):
    flow = _cron_flow(cron="kein gültiger cron")
    monkeypatch.setattr(sched.bp, "list_flows", lambda owner=None: [flow])
    fired = await sched._tick(datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC), datetime(2026, 6, 5, 10, 1, 0, tzinfo=UTC))
    assert fired == 0
    assert capture_dispatch == []


async def test_run_loop_ruft_tick_und_stoppt(monkeypatch):
    monkeypatch.setattr(sched, "_STARTUP_DELAY", 0.0)
    monkeypatch.setattr(sched, "_TICK_INTERVAL", 0.01)
    ticks = 0

    async def fake_tick(since, now):
        nonlocal ticks
        ticks += 1
        return 0

    monkeypatch.setattr(sched, "_tick", fake_tick)
    stop = asyncio.Event()
    task = asyncio.create_task(sched.run_loop(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)
    assert ticks >= 1
