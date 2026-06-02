"""Tool-Confirmation-Primitives (Issue #205, kritischer Pfad).

Gate für require_tool_confirm: register/resolve/wait/cancel steuern, ob ein Tool
ausgeführt wird. Default bei fehlender/abgelaufener Bestätigung ist 'deny'
(fail-safe).
"""
from __future__ import annotations

import asyncio

from hydrahive.runner import tool_confirmation as tc


def _run(coro):
    return asyncio.run(coro)


def test_register_then_approve():
    async def body():
        tc._pending.clear()
        fut = tc.register("c1")
        assert tc.resolve("c1", "approve") is True
        assert await fut == "approve"
    _run(body())


def test_register_then_deny():
    async def body():
        tc._pending.clear()
        fut = tc.register("c2")
        assert tc.resolve("c2", "deny") is True
        assert await fut == "deny"
    _run(body())


def test_resolve_missing_returns_false():
    async def body():
        tc._pending.clear()
        assert tc.resolve("nope", "approve") is False
    _run(body())


def test_wait_without_pending_denies():
    async def body():
        tc._pending.clear()
        assert await tc.wait("never-registered") == "deny"
    _run(body())


def test_wait_timeout_denies_and_clears():
    async def body():
        tc._pending.clear()
        tc.register("c3")
        decision = await tc.wait("c3", timeout=0.01)
        assert decision == "deny"
        assert "c3" not in tc._pending
    _run(body())


def test_cancel_cancels_future():
    async def body():
        tc._pending.clear()
        fut = tc.register("c4")
        tc.cancel("c4")
        assert fut.cancelled()
    _run(body())


def test_register_requires_running_loop():
    # #210 (L3): register() bindet die Future an den LAUFENDEN Loop
    # (get_running_loop statt deprecated get_event_loop). Ohne Loop → RuntimeError.
    import pytest
    tc._pending.clear()
    with pytest.raises(RuntimeError):
        tc.register("no-loop")
