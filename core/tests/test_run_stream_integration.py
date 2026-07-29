"""Integration: entkoppelter Run + lückenloses Streaming über den Event-Bus.

Beweist: (1) der Sende-Stream bekommt alle Events flüssig, (2) reißt er ab,
läuft der Run weiter, (3) ein Reconnect-Stream bekommt die verpassten Events
lückenlos nachgeliefert, (4) Stop cancelt den Run.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.api.routes import _session_msg_helpers as H
from hydrahive.runner import concurrency as C
from hydrahive.runner.event_bus import bus
from hydrahive.runner.events import Done, TextDelta


async def _drain(response, limit=None):
    """Sammelt die SSE-Frames aus einer StreamingResponse."""
    frames = []
    async for chunk in response.body_iterator:
        frames.append(chunk)
        if limit and len(frames) >= limit:
            break
    return frames


@pytest.mark.asyncio
async def test_sender_stream_gets_all_events(monkeypatch):
    async def fake_runner(session_id, user_content, **kw):
        yield TextDelta(text="Hal")
        await asyncio.sleep(0.01)
        yield TextDelta(text="lo")
        yield Done(message_id="m1", iterations=1)

    monkeypatch.setattr(H, "runner_run", fake_runner)

    resp = await H.run_and_stream("int-1", "hi")
    frames = await _drain(resp)
    joined = "".join(frames)
    assert "Hal" in joined and "lo" in joined
    assert "event: done" in joined
    # Run ist danach beendet
    for _ in range(50):
        if not C.is_running("int-1"):
            break
        await asyncio.sleep(0.02)
    assert not C.is_running("int-1")


@pytest.mark.asyncio
async def test_run_survives_sender_disconnect_and_reconnect_is_gapless(monkeypatch):
    gate = asyncio.Event()

    async def fake_runner(session_id, user_content, **kw):
        yield TextDelta(text="A")   # seq 1
        yield TextDelta(text="B")   # seq 2
        await gate.wait()           # hält den Run offen
        yield TextDelta(text="C")   # seq 3
        yield Done(message_id="m1", iterations=1)  # seq 4

    monkeypatch.setattr(H, "runner_run", fake_runner)

    # Sender startet, liest die ersten 2 Events, dann "Browser zu" (Stream weg)
    resp = await H.run_and_stream("int-2", "hi")
    first = await _drain(resp, limit=2)
    assert "A" in "".join(first) and "B" in "".join(first)
    await resp.body_iterator.aclose()  # Verbindung abgerissen

    # Run läuft weiter (Task lebt)
    assert C.is_running("int-2")

    # Reconnect ab seq=2 → bekommt C und Done lückenlos
    gate.set()
    reconnect = await H.attach_stream("int-2", after_seq=2)
    frames = await _drain(reconnect)
    joined = "".join(frames)
    assert "C" in joined
    assert "event: done" in joined


@pytest.mark.asyncio
async def test_stop_cancels_running(monkeypatch):
    started = asyncio.Event()

    async def fake_runner(session_id, user_content, **kw):
        started.set()
        yield TextDelta(text="x")
        await asyncio.sleep(30)

    monkeypatch.setattr(H, "runner_run", fake_runner)

    H.start_run_task("int-stop", "hi")
    await asyncio.wait_for(started.wait(), timeout=2.0)
    assert C.is_running("int-stop")
    assert C.cancel("int-stop") is True
    for _ in range(50):
        if not C.is_running("int-stop"):
            break
        await asyncio.sleep(0.02)
    assert not C.is_running("int-stop")
    bus.close("int-stop")
