from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from hydrahive.butler import scheduler
from hydrahive.butler.models import Flow, Node, NodePosition

UTC = timezone.utc


def _flow() -> Flow:
    return Flow(
        flow_id="flow-1", name="Cron", owner="alice", enabled=True,
        nodes=[Node(
            id="trigger", type="trigger", subtype="cron_fired",
            position=NodePosition(x=0, y=0), params={"cron": "* * * * *"},
        )],
    )


def _window(minute: int = 1):
    return (
        datetime(2026, 6, 5, 10, minute - 1, tzinfo=UTC),
        datetime(2026, 6, 5, 10, minute, tzinfo=UTC),
    )


async def test_zweiter_tick_waehrend_lauf_ueberspringt_flow(monkeypatch, caplog):
    started = asyncio.Event()
    release = asyncio.Event()
    finished = asyncio.Event()
    calls = 0

    async def dispatch(flow, event):
        nonlocal calls
        calls += 1
        started.set()
        try:
            await release.wait()
        finally:
            finished.set()
        return {"matched": True, "actions_executed": []}

    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [_flow()])
    monkeypatch.setattr(scheduler.bex, "dispatch", dispatch)
    first_tick = asyncio.create_task(scheduler._tick(*_window()))
    await asyncio.wait_for(started.wait(), timeout=0.2)
    try:
        with caplog.at_level("INFO", logger=scheduler.__name__):
            second_count = await asyncio.wait_for(scheduler._tick(*_window(2)), timeout=0.1)
    finally:
        release.set()
        await asyncio.gather(first_tick, return_exceptions=True)
        await asyncio.wait_for(finished.wait(), timeout=0.2)

    assert second_count == 0
    assert calls == 1
    assert "läuft bereits" in caplog.text


async def test_cron_lauf_wird_nach_zeitlimit_abgebrochen(monkeypatch, caplog):
    cancelled = asyncio.Event()

    async def dispatch(flow, event):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(scheduler, "_RUN_TIMEOUT_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [_flow()])
    monkeypatch.setattr(scheduler.bex, "dispatch", dispatch)

    with caplog.at_level("ERROR", logger=scheduler.__name__):
        fired = await asyncio.wait_for(scheduler._tick(*_window()), timeout=0.2)
        await asyncio.wait_for(cancelled.wait(), timeout=0.2)

    assert fired == 1
    assert "Zeitlimit" in caplog.text


async def test_verpasste_zeitpunkte_werden_pro_flow_zusammengefasst(monkeypatch):
    calls = 0

    async def dispatch(flow, event):
        nonlocal calls
        calls += 1
        return {"matched": True, "actions_executed": []}

    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [_flow()])
    monkeypatch.setattr(scheduler.bex, "dispatch", dispatch)

    fired = await scheduler._tick(
        datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
        datetime(2026, 6, 5, 10, 3, tzinfo=UTC),
    )
    await asyncio.sleep(0)

    assert fired == 1
    assert calls == 1
