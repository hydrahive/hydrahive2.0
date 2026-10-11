"""Warten statt Ablehnen (docs/specs/harakiri-confirm-noise.md, Punkt 3).

- Chat-Läufe (origin chat/delegation): ohne Zeitlimit warten (HH_TOOL_CONFIRM_TIMEOUT_CHAT, 0 = ohne).
- Läufe ohne Fenster: Limit HH_TOOL_CONFIRM_TIMEOUT (300 s); Ablauf ≠ Ablehnung.
- run-status liefert die offene Bestätigung (Banner nach Neuladen).
- Stopp während des Wartens räumt die offene Bestätigung auf.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.runner import _runner_tools, tool_confirmation as tc
from hydrahive.runner.events import ToolConfirmRequired, ToolUseResult
from hydrahive.tools._launcher import DevLauncher, LaunchResult, set_launcher
from hydrahive.tools.base import ToolContext, ToolResult

PROTECTED = {"id": "c1", "name": "shell_exec", "input": {"cmd": "touch /etc/x"}}


class FakeLauncher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run(self, cmd, cwd, timeout=60, env=None):
        self.calls.append(cmd)
        return LaunchResult(exit_code=0, stdout="ok", stderr="")


@pytest.fixture
def launcher(monkeypatch):
    fake = FakeLauncher()
    set_launcher(fake)
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)

    async def _exec(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        # Ausführung ohne DB-Protokoll: nur der Launcher-Aufruf zählt.
        await fake.run(tool_use["input"]["cmd"], ctx.workspace)
        return ToolResult.ok("ok"), "rec1", 1

    monkeypatch.setattr(_runner_tools, "execute_tool", _exec)
    tc._pending.clear()
    yield fake
    set_launcher(DevLauncher())
    tc._pending.clear()


def _ctx(ws: Path, origin: str) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="", user_id="u1", workspace=ws, origin=origin)


async def _collect(ctx, tool_uses=(PROTECTED,), on_confirm=None):
    events = []
    async for item in _runner_tools.process_tool_uses(
        list(tool_uses), ctx=ctx, allowed_tools=["shell_exec"],
        parent_message_id="m1", require_confirm=False, tool_result_max_chars=10000,
    ):
        events.append(item)
        if isinstance(item, ToolConfirmRequired) and on_confirm:
            on_confirm(item)
    return events


# --- Store -------------------------------------------------------------------

def test_wait_without_timeout_waits_until_resolved():
    async def body():
        tc.register("w1", session_id="s1")
        waiter = asyncio.create_task(tc.wait("w1", timeout=None))
        await asyncio.sleep(0.05)
        assert not waiter.done()
        tc.resolve("w1", "approve")
        assert await waiter == "approve"
    asyncio.run(body())


def test_timeout_is_not_a_denial():
    async def body():
        tc.register("w2", session_id="s1")
        assert await tc.wait("w2", timeout=0.01) == "timeout"
        assert tc.pending_for("s1") is None
    asyncio.run(body())


def test_pending_for_returns_display_data():
    async def body():
        tc.register("w3", session_id="s9", tool_name="shell_exec", arguments={"cmd": "x"}, reason="Grund")
        assert tc.pending_for("s9") == {
            "call_id": "w3", "tool_name": "shell_exec", "arguments": {"cmd": "x"}, "reason": "Grund",
        }
        assert tc.pending_for("andere") is None
        tc.resolve("w3", "deny")
        assert tc.pending_for("s9") is None
    asyncio.run(body())


def test_cancelled_wait_clears_pending():
    async def body():
        tc.register("w4", session_id="s1")
        waiter = asyncio.create_task(tc.wait("w4", timeout=None))
        await asyncio.sleep(0.01)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert tc.pending_for("s1") is None and "w4" not in tc._pending
    asyncio.run(body())


# --- Runner ------------------------------------------------------------------

def test_chat_run_waits_longer_than_old_limit(launcher, monkeypatch, tmp_path):
    """Chat-Lauf: Standard ohne Limit. Mit 0,05 s als 'altes' Limit für Läufe ohne Fenster
    muss der Chat-Lauf trotzdem auf die (spätere) Entscheidung warten und dann ausführen."""
    monkeypatch.setenv("HH_TOOL_CONFIRM_TIMEOUT", "0.05")
    monkeypatch.delenv("HH_TOOL_CONFIRM_TIMEOUT_CHAT", raising=False)

    async def body():
        def later(ev):
            asyncio.get_running_loop().call_later(0.2, tc.resolve, ev.call_id, "approve")
        return await _collect(_ctx(tmp_path, "chat"), on_confirm=later)

    events = asyncio.run(body())
    res = [e for e in events if isinstance(e, ToolUseResult)]
    assert res and res[0].success is True
    assert launcher.calls == ["touch /etc/x"]


def test_background_run_times_out_with_own_message(launcher, monkeypatch, tmp_path):
    monkeypatch.setenv("HH_TOOL_CONFIRM_TIMEOUT", "0.05")
    events = asyncio.run(_collect(_ctx(tmp_path, "other")))
    res = [e for e in events if isinstance(e, ToolUseResult)]
    assert res and res[0].success is False
    assert "Keine Antwort" in (res[0].error or "") and "abgelehnt" not in (res[0].error or "")
    assert launcher.calls == []
    assert tc.pending_for("s1") is None


def test_chat_limit_configurable(launcher, monkeypatch, tmp_path):
    monkeypatch.setenv("HH_TOOL_CONFIRM_TIMEOUT_CHAT", "0.05")
    events = asyncio.run(_collect(_ctx(tmp_path, "delegation")))
    res = [e for e in events if isinstance(e, ToolUseResult)]
    assert res and "Keine Antwort" in (res[0].error or "")
    assert launcher.calls == []


def test_explicit_deny_still_says_denied(launcher, monkeypatch, tmp_path):
    def deny(ev):
        tc.resolve(ev.call_id, "deny")
    events = asyncio.run(_collect(_ctx(tmp_path, "chat"), on_confirm=deny))
    res = [e for e in events if isinstance(e, ToolUseResult)]
    assert res and res[0].error == "Vom Benutzer abgelehnt"
    assert launcher.calls == []


def test_pending_visible_while_runner_waits(launcher, monkeypatch, tmp_path):
    seen = {}

    async def body():
        def look(ev):
            seen["p"] = tc.pending_for("s1")
            asyncio.get_running_loop().call_soon(tc.resolve, ev.call_id, "approve")
        await _collect(_ctx(tmp_path, "chat"), on_confirm=look)

    asyncio.run(body())
    assert seen["p"]["call_id"] == "c1" and seen["p"]["tool_name"] == "shell_exec"
    assert "/etc" in seen["p"]["reason"] and seen["p"]["arguments"] == {"cmd": "touch /etc/x"}
    assert tc.pending_for("s1") is None


def test_stop_while_waiting_leaves_no_pending(launcher, tmp_path):
    async def body():
        task = asyncio.create_task(_collect(_ctx(tmp_path, "chat")))
        for _ in range(50):
            await asyncio.sleep(0.01)
            if tc.pending_for("s1"):
                break
        assert tc.pending_for("s1") is not None
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(body())
    assert tc.pending_for("s1") is None and tc._pending == {}
    assert launcher.calls == []
