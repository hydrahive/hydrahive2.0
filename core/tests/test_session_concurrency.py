"""Tests für Session-Concurrency-Guard (Token-Audit #129 follow-up).

Hintergrund: Iter 1 doppelt mit Modell-Wechsel war ein paralleler run().
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.runner.concurrency import (
    SessionAlreadyRunning,
    active_count,
    force_release,
    is_running,
    session_run_guard,
)


def _run(coro):
    return asyncio.run(coro)


def test_guard_acquired_und_released_normal():
    sid = "test-concurrency-1"

    async def go():
        assert not is_running(sid)
        async with session_run_guard(sid):
            assert is_running(sid)
        assert not is_running(sid)

    _run(go())


def test_zweiter_run_wirft_session_already_running():
    sid = "test-concurrency-2"

    async def go():
        async with session_run_guard(sid):
            with pytest.raises(SessionAlreadyRunning) as exc_info:
                async with session_run_guard(sid):
                    pass
            assert exc_info.value.session_id == sid

    _run(go())


def test_release_bei_exception_im_block():
    sid = "test-concurrency-3"

    async def go():
        with pytest.raises(RuntimeError, match="boom"):
            async with session_run_guard(sid):
                raise RuntimeError("boom")
        assert not is_running(sid)

    _run(go())


def test_unabhaengige_sessions_blockieren_sich_nicht():
    async def go():
        s1, s2 = "test-c4-a", "test-c4-b"
        async with session_run_guard(s1):
            async with session_run_guard(s2):
                assert is_running(s1)
                assert is_running(s2)
                assert active_count() >= 2
        assert not is_running(s1)
        assert not is_running(s2)

    _run(go())


def test_force_release_entfernt_lock():
    sid = "test-c5"

    async def go():
        async with session_run_guard(sid):
            assert is_running(sid)
            assert force_release(sid) is True
            assert not is_running(sid)
            async with session_run_guard(sid):
                assert is_running(sid)

    _run(go())


def test_force_release_unbekannt_returnt_false():
    assert force_release("nie-gesehen") is False


def test_paralleler_acquire_einer_gewinnt():
    """Realistisches Szenario: zwei Tasks gleichzeitig — genau einer kommt durch."""

    async def go():
        sid = "test-c6-parallel"
        results: list[str] = []

        async def attempt(name: str) -> None:
            try:
                async with session_run_guard(sid):
                    results.append(f"{name}:ok")
                    await asyncio.sleep(0.05)
            except SessionAlreadyRunning:
                results.append(f"{name}:blocked")

        await asyncio.gather(attempt("A"), attempt("B"))

        ok_count = sum(1 for r in results if r.endswith(":ok"))
        blocked_count = sum(1 for r in results if r.endswith(":blocked"))
        assert ok_count == 1
        assert blocked_count == 1

    _run(go())
