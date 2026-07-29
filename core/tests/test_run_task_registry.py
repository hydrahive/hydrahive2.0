"""Task-Registry für entkoppelte Runs (chat-run-decoupled Task 1).

Der Run läuft als eigenständiger asyncio.Task, den man gezielt stoppen kann —
auch wenn die auslösende HTTP-Verbindung längst weg ist.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.runner import concurrency as C


@pytest.mark.asyncio
async def test_register_and_get_task():
    sid = "reg-1"
    task = asyncio.current_task()
    C.register_task(sid, task)
    try:
        assert C.get_task(sid) is task
        assert C.is_running(sid)  # registrierter Task = läuft
    finally:
        C.unregister_task(sid)
    assert C.get_task(sid) is None
    assert not C.is_running(sid)


@pytest.mark.asyncio
async def test_cancel_stops_running_task():
    sid = "reg-cancel"
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def long_run():
        C.register_task(sid, asyncio.current_task())
        started.set()
        try:
            await asyncio.sleep(30)  # simuliert langen Lauf
        except asyncio.CancelledError:
            cancelled.set()
            raise
        finally:
            C.unregister_task(sid)

    task = asyncio.create_task(long_run())
    await started.wait()
    assert C.is_running(sid)

    # Stop-Button: cancel über die Registry (nicht über die Verbindung)
    assert C.cancel(sid) is True
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()
    assert not C.is_running(sid)


@pytest.mark.asyncio
async def test_cancel_unknown_returns_false():
    assert C.cancel("nie-gestartet") is False


@pytest.mark.asyncio
async def test_is_running_reflects_registry_or_guard():
    """is_running muss sowohl den Guard (Set) als auch die Task-Registry sehen."""
    sid = "reg-both"
    async with C.session_run_guard(sid):
        assert C.is_running(sid)
    assert not C.is_running(sid)
