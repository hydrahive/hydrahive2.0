"""Tests für shell_exec — Reject-Pfade, Env-Filter, Cmd-Rewrite, Launcher-Aufruf.

Wir mocken den Launcher (set_launcher) und prüfen was shell._execute()
an ihn weiterreicht — kein echter Subprocess, keine Workspace-IO.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from hydrahive.tools import shell
from hydrahive.tools._launcher import LaunchResult, set_launcher
from hydrahive.tools.base import ToolContext


class FakeLauncher:
    """Sammelt Aufruf-Args, gibt das vorab eingestellte Result zurück."""

    def __init__(self, result: LaunchResult | None = None):
        self.calls: list[dict] = []
        self.result = result or LaunchResult(exit_code=0, stdout="ok", stderr="")

    async def run(self, cmd: str, cwd: Path, timeout: int = 60, env: dict | None = None):
        self.calls.append({"cmd": cmd, "cwd": cwd, "timeout": timeout, "env": env or {}})
        return self.result


def _ctx(workspace: Path) -> ToolContext:
    return ToolContext(
        session_id="s1", agent_id="", user_id="u1", workspace=workspace,
    )


def _run(args: dict, ctx: ToolContext):
    return asyncio.run(shell._execute(args, ctx))


@pytest.fixture
def launcher():
    fake = FakeLauncher()
    set_launcher(fake)
    yield fake
    from hydrahive.tools._launcher import DevLauncher
    set_launcher(DevLauncher())


def test_leerer_befehl_wird_abgelehnt(launcher, tmp_path):
    res = _run({"cmd": ""}, _ctx(tmp_path))
    assert not res.success
    assert "Leerer Befehl" in res.error
    assert launcher.calls == []


def test_whitespace_only_wird_abgelehnt(launcher, tmp_path):
    res = _run({"cmd": "   \t  "}, _ctx(tmp_path))
    assert not res.success
    assert launcher.calls == []


def test_mmx_speech_wird_blockiert(launcher, tmp_path):
    res = _run({"cmd": "mmx speech --text 'hallo'"}, _ctx(tmp_path))
    assert not res.success
    assert "tts" in res.error.lower() or "speech" in res.error.lower()
    assert launcher.calls == []


def test_mmx_tts_wird_blockiert(launcher, tmp_path):
    res = _run({"cmd": "mmx tts --voice female"}, _ctx(tmp_path))
    assert not res.success
    assert launcher.calls == []


def test_normaler_mmx_aufruf_durchgelassen(launcher, tmp_path):
    _run({"cmd": "mmx music generate --prompt jazz"}, _ctx(tmp_path))
    assert len(launcher.calls) == 1


def test_mmx_music_ohne_model_bekommt_default_modell(launcher, tmp_path):
    _run({"cmd": "mmx music generate --prompt jazz"}, _ctx(tmp_path))
    assert "--model music-2.6" in launcher.calls[0]["cmd"]


def test_mmx_music_mit_model_bleibt_unveraendert(launcher, tmp_path):
    cmd = "mmx music generate --model music-1.5 --prompt jazz"
    _run({"cmd": cmd}, _ctx(tmp_path))
    assert launcher.calls[0]["cmd"].count("--model") == 1
    assert "--model music-1.5" in launcher.calls[0]["cmd"]


def test_timeout_zu_klein_wird_abgelehnt(launcher, tmp_path):
    res = _run({"cmd": "echo hi", "timeout": 0}, _ctx(tmp_path))
    assert not res.success
    assert "Timeout" in res.error
    assert launcher.calls == []


def test_timeout_zu_gross_wird_abgelehnt(launcher, tmp_path):
    res = _run({"cmd": "echo hi", "timeout": 601}, _ctx(tmp_path))
    assert not res.success
    assert launcher.calls == []


def test_default_timeout_ist_60(launcher, tmp_path):
    _run({"cmd": "echo hi"}, _ctx(tmp_path))
    assert launcher.calls[0]["timeout"] == 60


def test_custom_timeout_wird_durchgereicht(launcher, tmp_path):
    _run({"cmd": "echo hi", "timeout": 120}, _ctx(tmp_path))
    assert launcher.calls[0]["timeout"] == 120


def test_cwd_ist_die_workspace(launcher, tmp_path):
    _run({"cmd": "echo hi"}, _ctx(tmp_path))
    assert launcher.calls[0]["cwd"] == tmp_path


def test_secret_keys_werden_aus_env_entfernt(launcher, tmp_path, monkeypatch):
    monkeypatch.setenv("HH_SECRET_KEY", "supersecret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oa-xxx")
    monkeypatch.setenv("HH_PG_MIRROR_DSN", "postgresql://creds@host/db")
    monkeypatch.setenv("PATH", "/usr/bin")
    _run({"cmd": "echo hi"}, _ctx(tmp_path))
    env = launcher.calls[0]["env"]
    assert "HH_SECRET_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert "OPENAI_API_KEY" not in env
    assert "HH_PG_MIRROR_DSN" not in env
    assert env.get("PATH") == "/usr/bin"


def test_erfolgs_ergebnis_enthaelt_stdout_stderr_exit(launcher, tmp_path):
    launcher.result = LaunchResult(exit_code=0, stdout="hello\n", stderr="")
    res = _run({"cmd": "echo hello"}, _ctx(tmp_path))
    assert res.success
    assert res.output["stdout"] == "hello\n"
    assert res.output["stderr"] == ""
    assert res.output["exit_code"] == 0


def test_nonzero_exit_ist_kein_fail(launcher, tmp_path):
    """shell_exec liefert nonzero exit als success=True zurück — die LLM
    sieht den exit_code im output und entscheidet was zu tun ist."""
    launcher.result = LaunchResult(exit_code=1, stdout="", stderr="boom")
    res = _run({"cmd": "false"}, _ctx(tmp_path))
    assert res.success
    assert res.output["exit_code"] == 1
    assert res.output["stderr"] == "boom"


def test_timeout_ergebnis_ist_fail_mit_flag(launcher, tmp_path):
    launcher.result = LaunchResult(exit_code=-1, stdout="", stderr="", timed_out=True)
    res = _run({"cmd": "sleep 999", "timeout": 5}, _ctx(tmp_path))
    assert not res.success
    assert res.output["timed_out"] is True
    assert "Timeout nach 5s" in res.error
