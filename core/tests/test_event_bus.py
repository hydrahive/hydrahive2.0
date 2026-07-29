"""Session-Event-Bus (chat-run-decoupled Task 2a).

Lückenloser Event-Stream pro Session: der entkoppelte Run publisht Events mit
fortlaufender seq; Consumer lesen ab ihrem Cursor weiter — auch nach Reconnect
mitten im Lauf, ohne Token zu verlieren.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.runner.event_bus import SessionEventBus


@pytest.mark.asyncio
async def test_publish_assigns_increasing_seq():
    bus = SessionEventBus(capacity=100)
    sid = "bus-1"
    assert bus.publish(sid, {"type": "TextDelta", "text": "a"}) == 1
    assert bus.publish(sid, {"type": "TextDelta", "text": "b"}) == 2
    assert bus.latest_seq(sid) == 2


@pytest.mark.asyncio
async def test_subscriber_gets_live_events():
    bus = SessionEventBus(capacity=100)
    sid = "bus-live"
    received = []

    async def consume():
        async for seq, ev in bus.subscribe(sid, after_seq=0):
            received.append((seq, ev["text"]))
            if ev.get("type") == "Done":
                break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    bus.publish(sid, {"type": "TextDelta", "text": "hallo"})
    bus.publish(sid, {"type": "Done", "text": "x"})
    await asyncio.wait_for(task, timeout=2.0)
    assert received == [(1, "hallo"), (2, "x")]


@pytest.mark.asyncio
async def test_reconnect_gets_missed_events_from_buffer():
    """Ein Client der ab seq=1 wieder einsteigt, bekommt die verpassten 2,3,… ."""
    bus = SessionEventBus(capacity=100)
    sid = "bus-reconnect"
    bus.publish(sid, {"type": "TextDelta", "text": "1"})  # seq 1
    bus.publish(sid, {"type": "TextDelta", "text": "2"})  # seq 2
    bus.publish(sid, {"type": "TextDelta", "text": "3"})  # seq 3

    got = []

    async def consume():
        async for seq, ev in bus.subscribe(sid, after_seq=1):
            got.append((seq, ev["text"]))
            if seq >= 3:
                break

    task = asyncio.create_task(consume())
    await asyncio.wait_for(task, timeout=2.0)
    # bekommt 2 und 3 aus dem Puffer nachgeliefert (1 hatte er schon)
    assert got == [(2, "2"), (3, "3")]


@pytest.mark.asyncio
async def test_buffer_eviction_reports_gap():
    """Fällt der Cursor aus dem Ringpuffer, meldet subscribe einen Gap
    (Client muss aus DB nachladen)."""
    bus = SessionEventBus(capacity=3)
    sid = "bus-evict"
    for i in range(1, 6):  # seq 1..5, Puffer hält nur letzte 3 (3,4,5)
        bus.publish(sid, {"type": "TextDelta", "text": str(i)})

    # Cursor after_seq=1: 2 ist schon evicted -> Gap gemeldet
    assert bus.has_gap(sid, after_seq=1) is True
    # Cursor after_seq=3: 4,5 noch da -> kein Gap
    assert bus.has_gap(sid, after_seq=3) is False


@pytest.mark.asyncio
async def test_close_ends_subscribers():
    bus = SessionEventBus(capacity=100)
    sid = "bus-close"
    ended = asyncio.Event()

    async def consume():
        async for _seq, _ev in bus.subscribe(sid, after_seq=0):
            pass
        ended.set()

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    bus.publish(sid, {"type": "TextDelta", "text": "x"})
    bus.close(sid)  # Run zu Ende -> Subscriber-Iteratoren enden
    await asyncio.wait_for(ended.wait(), timeout=2.0)
    assert ended.is_set()
    task.cancel()
