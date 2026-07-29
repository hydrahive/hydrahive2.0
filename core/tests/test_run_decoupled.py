"""Entkoppelter Run-Start (chat-run-decoupled Task 2/3).

Kern: der Run läuft als eigenständiger Server-Task. Er überlebt, wenn der
Aufrufer (HTTP-Verbindung) verschwindet, und lässt sich über cancel() stoppen.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.api.routes import _session_msg_helpers as H
from hydrahive.runner import concurrency as C


@pytest.mark.asyncio
async def test_start_run_task_runs_to_completion_without_caller(monkeypatch):
    """Der Run läuft zu Ende, auch wenn niemand den Task awaited (Browser weg)."""
    done = asyncio.Event()
    steps: list[str] = []

    async def fake_runner(session_id, user_content, **kw):
        steps.append("start")
        await asyncio.sleep(0.05)
        steps.append("mid")
        await asyncio.sleep(0.05)
        steps.append("end")
        done.set()
        return
        yield  # macht es zum async generator

    monkeypatch.setattr(H, "runner_run", fake_runner)

    sid = "decoupled-1"
    H.start_run_task(sid, "hallo")
    # Aufrufer "verschwindet" sofort — wir awaiten den Task NICHT.
    assert C.is_running(sid)
    await asyncio.wait_for(done.wait(), timeout=2.0)
    # kurz aufräumen lassen
    await asyncio.sleep(0.02)
    assert steps == ["start", "mid", "end"]
    assert not C.is_running(sid)


@pytest.mark.asyncio
async def test_start_run_task_cancel_stops_it(monkeypatch):
    """cancel() stoppt den laufenden Run mitten drin (Stop-Button-Fall)."""
    started = asyncio.Event()

    async def fake_runner(session_id, user_content, **kw):
        started.set()
        await asyncio.sleep(30)
        return
        yield

    monkeypatch.setattr(H, "runner_run", fake_runner)

    sid = "decoupled-cancel"
    H.start_run_task(sid, "lang")
    await asyncio.wait_for(started.wait(), timeout=2.0)
    assert C.is_running(sid)

    assert C.cancel(sid) is True
    # Registry wird sauber freigegeben
    for _ in range(50):
        if not C.is_running(sid):
            break
        await asyncio.sleep(0.02)
    assert not C.is_running(sid)


@pytest.mark.asyncio
async def test_start_run_task_second_start_blocked(monkeypatch):
    """Variante A: zweiter Start bei laufendem Run wird abgelehnt (kein Doppellauf)."""
    async def fake_runner(session_id, user_content, **kw):
        await asyncio.sleep(0.3)
        return
        yield

    monkeypatch.setattr(H, "runner_run", fake_runner)

    sid = "decoupled-double"
    H.start_run_task(sid, "erst")
    assert C.is_running(sid)
    with pytest.raises(H.SessionAlreadyRunning):
        H.start_run_task(sid, "zweit")
    C.cancel(sid)
    for _ in range(50):
        if not C.is_running(sid):
            break
        await asyncio.sleep(0.02)
