"""docs/specs/projekt-container-ausfuehrung.md (K1a): Launcher-Auswahl und ContainerLauncher (incus als Attrappe)."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from hydrahive.tools import _launcher_container, shell
from hydrahive.tools._launcher import DevLauncher, LaunchResult, set_launcher
from hydrahive.tools.base import ToolContext

def _ctx(project_id: str | None) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=Path("/tmp/hh-k1-ws"),
                       project_id=project_id)


# --- ContainerLauncher ------------------------------------------------------------------------------------------

class _Proc:
    def __init__(self, rc=0, out=b"ok\n", err=b"", hang=False):
        self.returncode = None
        self._rc, self._out, self._err, self._hang = rc, out, err, hang
        self.pid = 4242
        self.killed = False

    async def communicate(self):
        if self._hang:
            await asyncio.sleep(3600)
        self.returncode = self._rc
        return self._out, self._err

    def kill(self):
        self.killed = True

    async def wait(self):
        self.returncode = -9
        return -9


@pytest.fixture
def fake_incus(monkeypatch):
    calls: list[dict] = []
    state = {"running": True, "proc": None, "hang": False}

    async def fake_exec(*args, **kw):
        calls.append({"args": list(args), "env": dict(kw.get("env") or {}), "kw": kw})
        if args[:2] == ("incus", "list"):
            p = _Proc(out=b"RUNNING\n" if state["running"] else b"STOPPED\n")
            return p
        if "pkill" in " ".join(args):
            return _Proc(out=b"")
        p = _Proc(hang=state["hang"])
        state["proc"] = p
        return p

    monkeypatch.setattr(_launcher_container.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(_launcher_container, "_INCUS", "incus")
    return {"calls": calls, "state": state}


def _lc():
    return _launcher_container.ContainerLauncher("hh-labor-probe", "/work", 1000)


def _exec_calls(calls):
    return [c for c in calls if c["args"][:2] == ["incus", "exec"]]


def test_befehl_als_ein_argument_ohne_host_shell(fake_incus):
    cmd = "echo a; echo $(id) `whoami` && cat <<'X'\nY\nX\n echo 'q\"' > /tmp/x"
    res = asyncio.run(_lc().run(cmd, Path("/egal"), timeout=10, env={"GH_TOKEN": "ghp_GEHEIM"}))
    assert res.exit_code == 0 and res.stdout == "ok\n"
    ex = _exec_calls(fake_incus["calls"])
    assert len(ex) == 1
    a = ex[0]["args"]
    assert a[:3] == ["incus", "exec", "hh-labor-probe"]
    i = a.index("--")
    assert a[i + 1:i + 3] == ["setsid", "bash"]
    assert a[-1] == cmd                               # Befehl unverändert, als genau ein Argument am Ende
    assert cmd not in a[i + 4]                        # nie in den Wrapper-Text eingesetzt
    assert 'bash -lc "$1"' in a[i + 4]
    assert ["--cwd", "/work"] == a[a.index("--cwd"):a.index("--cwd") + 2]
    assert ["--user", "1000"] == a[a.index("--user"):a.index("--user") + 2]
    assert ["--group", "1000"] == a[a.index("--group"):a.index("--group") + 2]
    assert ex[0]["kw"].get("shell") is not True


def test_befehl_darf_nicht_als_incus_option_gelten(fake_incus):
    asyncio.run(_lc().run("--project=evil", Path("/egal")))
    a = _exec_calls(fake_incus["calls"])[0]["args"]
    assert a.index("--project=evil") > a.index("--")


def test_keine_server_umgebung_im_container(fake_incus, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ghp_SERVER")
    monkeypatch.setenv("HH_SECRET_KEY", "server-secret")
    asyncio.run(_lc().run("env", Path("/egal"), env={"GH_TOKEN": "ghp_GEHEIM", "GITEA_TOKEN": "g", "PATH": "/x"}))
    c = _exec_calls(fake_incus["calls"])[0]
    text = " ".join(c["args"]) + " " + " ".join(f"{k}={v}" for k, v in c["env"].items())
    for s in ("ghp_GEHEIM", "ghp_SERVER", "server-secret", "GITEA_TOKEN", "HH_SECRET_KEY"):
        assert s not in text
    # auch der Host-Prozess (incus selbst) bekommt nur PATH – sonst sähe ein incus-Wrapper die Server-Geheimnisse
    assert c["env"] == {"PATH": "/usr/bin:/bin"}
    envs = [c["args"][i + 1] for i, x in enumerate(c["args"]) if x == "--env"]
    assert sorted(envs) == sorted(["HOME=/home/labor", "LANG=C.UTF-8", "HH_EXEC_ID=" + envs_id(envs)])


def envs_id(envs):
    return next(e.split("=", 1)[1] for e in envs if e.startswith("HH_EXEC_ID="))


def test_container_aus_klarer_fehler_kein_start(fake_incus):
    fake_incus["state"]["running"] = False
    with pytest.raises(_launcher_container.ContainerDown):
        asyncio.run(_lc().run("echo hi", Path("/egal")))
    assert not _exec_calls(fake_incus["calls"])
    assert not any(c["args"][:2] == ["incus", "start"] for c in fake_incus["calls"])


def test_zeitlimit_beendet_auch_im_container(fake_incus):
    fake_incus["state"]["hang"] = True
    res = asyncio.run(_lc().run("sleep 999", Path("/egal"), timeout=1))
    assert res.timed_out and res.exit_code == -1
    assert fake_incus["state"]["proc"].killed
    exec_id = envs_id([c for c in _exec_calls(fake_incus["calls"])][0]["args"][
        _exec_calls(fake_incus["calls"])[0]["args"].index("--env") + 1:])
    kills = [c for c in fake_incus["calls"] if c["args"][:2] == ["incus", "exec"] and "pkill" in " ".join(c["args"])]
    assert kills and any(f"/tmp/hh-exec-{exec_id}.pgid" in " ".join(k["args"]) for k in kills)
    assert all("--user" in k["args"] for k in kills)  # nie als root im Container killen


def test_abbruch_beendet_auch_im_container(fake_incus):
    fake_incus["state"]["hang"] = True

    async def go():
        t = asyncio.create_task(_lc().run("sleep 999", Path("/egal"), timeout=60))
        await asyncio.sleep(0.05)
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

    asyncio.run(go())
    assert fake_incus["state"]["proc"].killed
    assert any("pkill" in " ".join(c["args"]) for c in fake_incus["calls"])


def test_shell_exec_nimmt_den_projekt_launcher(monkeypatch, tmp_path):
    seen = {}

    class L:
        async def run(self, cmd, cwd, timeout=60, env=None):
            seen["cmd"] = cmd
            return LaunchResult(0, "drin", "")

    monkeypatch.setattr(_launcher_container, "launcher_for", lambda ctx: L())
    res = asyncio.run(shell._execute({"cmd": "echo hi"}, _ctx("p1")))
    assert res.success and seen["cmd"] == "echo hi"


def test_shell_exec_ohne_launcher_klarer_fehler(monkeypatch):
    def boom(ctx):
        raise _launcher_container.ExecutionUnavailable("project_execution_unavailable")

    monkeypatch.setattr(_launcher_container, "launcher_for", boom)
    res = asyncio.run(shell._execute({"cmd": "echo hi"}, _ctx("p1")))
    assert not res.success and "project_execution_unavailable" in (res.error or "")


def test_dev_launcher_unveraendert_fuer_host(monkeypatch, tmp_path):
    """Gegenprobe: ohne Container-Projekt bleibt alles wie heute (echter DevLauncher, kein incus)."""
    monkeypatch.setattr(_launcher_container.asyncio, "create_subprocess_exec",
                        lambda *a, **k: pytest.fail("incus bei Host-Projekt aufgerufen"))
    set_launcher(DevLauncher())
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=tmp_path)
    res = asyncio.run(shell._execute({"cmd": "echo host-$((1+1))"}, ctx))
    assert res.success and res.output["stdout"].strip() == "host-2"
    assert os.path.isdir(tmp_path)


