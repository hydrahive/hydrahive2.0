"""Harakiri-Schutz im Runner-Seam: shell_exec auf geschützten Pfad → Popup.

Beweist die Verdrahtung in process_tool_uses:
- Protected-Write ohne globales require_confirm → ToolConfirmRequired mit reason,
  und Deny verhindert die tatsächliche Ausführung (Launcher nie aufgerufen).
- Harmloser Befehl läuft ohne Confirm durch.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.runner import _runner_tools, tool_confirmation
from hydrahive.runner.events import ToolConfirmRequired, ToolUseResult
from hydrahive.tools._launcher import DevLauncher, LaunchResult, set_launcher
from hydrahive.tools.base import ToolContext, ToolResult


class FakeLauncher:
    def __init__(self):
        self.calls: list[str] = []

    async def run(self, cmd, cwd, timeout=60, env=None):
        self.calls.append(cmd)
        return LaunchResult(exit_code=0, stdout="ok", stderr="")


def _ctx(ws: Path) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="", user_id="u1", workspace=ws)


async def _drive(tool_uses, ctx):
    events = []
    async for item in _runner_tools.process_tool_uses(
        tool_uses, ctx=ctx, allowed_tools=["shell_exec"],
        parent_message_id="m1", require_confirm=False, tool_result_max_chars=10000,
    ):
        events.append(item)
    return events


@pytest.fixture
def launcher(monkeypatch):
    fake = FakeLauncher()
    set_launcher(fake)
    # Observation-Recording ist hier irrelevant und braucht Storage → no-op.
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    tool_confirmation._pending.clear()
    yield fake
    set_launcher(DevLauncher())
    tool_confirmation._pending.clear()


async def _deny(call_id, timeout=0):
    return "deny"


def test_protected_write_triggers_confirm_and_blocks_exec(launcher, monkeypatch, tmp_path):
    monkeypatch.setattr(tool_confirmation, "wait", _deny)
    events = asyncio.run(_drive(
        [{"id": "c1", "name": "shell_exec", "input": {"cmd": "rm -rf /opt/searxng"}}],
        _ctx(tmp_path),
    ))
    confirms = [e for e in events if isinstance(e, ToolConfirmRequired)]
    assert len(confirms) == 1
    assert confirms[0].reason and "/opt" in confirms[0].reason
    # Deny → Befehl wurde NIE ausgeführt
    assert launcher.calls == []
    results = [e for e in events if isinstance(e, ToolUseResult)]
    assert results and results[0].success is False


def test_secret_read_triggers_confirm(launcher, monkeypatch, tmp_path):
    monkeypatch.setattr(tool_confirmation, "wait", _deny)
    events = asyncio.run(_drive(
        [{"id": "c2", "name": "shell_exec", "input": {"cmd": "cat /etc/shadow"}}],
        _ctx(tmp_path),
    ))
    confirms = [e for e in events if isinstance(e, ToolConfirmRequired)]
    assert len(confirms) == 1
    assert confirms[0].reason and "Geheimnis" in confirms[0].reason
    assert launcher.calls == []


def test_benign_command_runs_without_confirm(launcher, monkeypatch, tmp_path):
    called = {"wait": False, "exec_cmd": None}

    async def _spy_wait(call_id, timeout=0):
        called["wait"] = True
        return "approve"

    async def _fake_exec(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        called["exec_cmd"] = tool_use["input"]["cmd"]
        return ToolResult.ok("ok"), "rec1", 5

    monkeypatch.setattr(tool_confirmation, "wait", _spy_wait)
    monkeypatch.setattr(_runner_tools, "execute_tool", _fake_exec)
    events = asyncio.run(_drive(
        [{"id": "c3", "name": "shell_exec", "input": {"cmd": "echo hi"}}],
        _ctx(tmp_path),
    ))
    # Kein Confirm-Pfad, Tool wurde direkt ausgeführt
    assert called["wait"] is False
    assert called["exec_cmd"] == "echo hi"
    assert [e for e in events if isinstance(e, ToolConfirmRequired)] == []
