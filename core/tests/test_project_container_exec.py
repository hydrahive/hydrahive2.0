"""docs/specs/projekt-container-ausfuehrung.md (K1a): Projekt-Ausführung im Container.

incus wird nie echt aufgerufen: `fake_incus` ersetzt den einzigen Ausführungsweg des ContainerLaunchers
(asyncio.create_subprocess_exec) und schreibt die Argumente mit. Echte Ausbruchsproben laufen auf hydratest.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from hydrahive.tools import _launcher, _launcher_container, shell
from hydrahive.tools._launcher import DevLauncher, LaunchResult, set_launcher
from hydrahive.tools.base import ToolContext


# --- Projekt-Einstellung -----------------------------------------------------------------------------------------

def _project(client, admin_headers) -> str:
    r = client.post("/api/projects", headers=admin_headers, json={"name": "Labor-Probe", "llm_model": "test/model"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture
def known_container(monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: name == "hh-labor-probe")


def test_ohne_einstellung_ist_es_der_server(client, admin_headers):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    assert execution.of(project_config.get(pid)) == {"mode": "host"}
    assert execution.of(None) == {"mode": "host"}


def test_container_setzen_ueber_kern_funktion(client, admin_headers, known_container):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    execution.set_container(pid, "hh-labor-probe", actor="admin")
    assert execution.of(project_config.get(pid)) == {"mode": "container", "container": "hh-labor-probe",
                                                     "workdir": "/work", "user": 1000}


@pytest.mark.parametrize("name", ["", "Grossbuchstabe", "1start", "a", "x;rm -rf /", "a b", "../x", "a" * 64,
                                  "-flag", "--project=evil"])
def test_ungueltiger_containername(client, admin_headers, name, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda n: True)
    pid = _project(client, admin_headers)
    with pytest.raises(execution.ExecutionError) as e:
        execution.set_container(pid, name, actor="admin")
    assert e.value.code == "project_container_invalid"


def test_unbekannter_container(client, admin_headers, known_container):
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    with pytest.raises(execution.ExecutionError) as e:
        execution.set_container(pid, "hh-gibt-es-nicht", actor="admin")
    assert e.value.code == "project_container_missing"


@pytest.mark.parametrize(("workdir", "user"), [("relativ", 1000), ("/", 1000), ("/work/../etc", 1000),
                                               ("/work", 0), ("/work", -1), ("/work", "1000")])
def test_ungueltiges_arbeitsverzeichnis_oder_nutzer(client, admin_headers, known_container, workdir, user):
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    with pytest.raises(execution.ExecutionError) as e:
        execution.set_container(pid, "hh-labor-probe", actor="admin", workdir=workdir, user=user)
    assert e.value.code == "project_container_invalid"


def test_patch_route_kann_execution_nicht_setzen(client, admin_headers):
    """Nur über die Kern-Funktion bzw. die eigene Admin-Route – nicht nebenbei über das normale PATCH."""
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    client.patch(f"/api/projects/{pid}", headers=admin_headers,
                 json={"execution": {"mode": "container", "container": "hh-labor-probe"}})
    assert execution.of(project_config.get(pid)) == {"mode": "host"}


def test_config_update_kann_execution_nicht_setzen(client, admin_headers):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    project_config.update(pid, execution={"mode": "container", "container": "hh-labor-probe"})
    assert execution.of(project_config.get(pid)) == {"mode": "host"}


def test_zurueck_auf_server_nur_ausdruecklich(client, admin_headers, known_container):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    execution.set_container(pid, "hh-labor-probe", actor="admin")
    with pytest.raises(execution.ExecutionError):
        execution.set_host(pid, actor="admin", confirm="")
    assert execution.of(project_config.get(pid))["mode"] == "container"
    execution.set_host(pid, actor="admin", confirm="Labor-Probe")
    assert execution.of(project_config.get(pid)) == {"mode": "host"}


def test_kaputter_eintrag_gilt_nicht_als_server(client, admin_headers):
    """Ein beschädigtes execution-Feld darf NIE still auf den Server zurückfallen."""
    from hydrahive.projects import execution
    for broken in ({"mode": "container"}, {"mode": "weird"}, {"mode": "container", "container": "X;y"}, "container",
                   {"mode": "container", "container": "hh-ok", "workdir": "/"}):
        with pytest.raises(execution.ExecutionError):
            execution.of({"id": "p", "execution": broken})


# --- Launcher-Auswahl ------------------------------------------------------------------------------------------

def _ctx(project_id: str | None) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=Path("/tmp/hh-k1-ws"),
                       project_id=project_id)


def test_launcher_ohne_projekt_ist_der_server(monkeypatch):
    sentinel = DevLauncher()
    set_launcher(sentinel)
    try:
        assert _launcher_container.launcher_for(_ctx(None)) is sentinel
    finally:
        set_launcher(DevLauncher())


def test_launcher_host_projekt_ist_der_server(monkeypatch):
    from hydrahive.projects import config as project_config
    monkeypatch.setattr(project_config, "get", lambda pid: {"id": pid})
    sentinel = DevLauncher()
    set_launcher(sentinel)
    try:
        assert _launcher_container.launcher_for(_ctx("p1")) is sentinel
    finally:
        set_launcher(DevLauncher())


def test_launcher_container_projekt(monkeypatch):
    from hydrahive.projects import config as project_config
    monkeypatch.setattr(project_config, "get", lambda pid: {"id": pid, "execution": {
        "mode": "container", "container": "hh-labor-probe", "workdir": "/work", "user": 1000}})
    lc = _launcher_container.launcher_for(_ctx("p1"))
    assert isinstance(lc, _launcher_container.ContainerLauncher)
    assert (lc.container, lc.workdir, lc.user) == ("hh-labor-probe", "/work", 1000)


def test_launcher_projekt_fehlt_kein_rueckfall(monkeypatch):
    from hydrahive.projects import config as project_config
    monkeypatch.setattr(project_config, "get", lambda pid: None)
    with pytest.raises(_launcher_container.ExecutionUnavailable):
        _launcher_container.launcher_for(_ctx("p1"))


def test_launcher_projekt_unlesbar_kein_rueckfall(monkeypatch):
    from hydrahive.projects import config as project_config

    def boom(pid):
        raise OSError("kaputt")

    monkeypatch.setattr(project_config, "get", boom)
    with pytest.raises(_launcher_container.ExecutionUnavailable):
        _launcher_container.launcher_for(_ctx("p1"))


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
        if "pkill" in args or "kill" in " ".join(args[-1:]):
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
    assert a[i + 1:i + 3] == ["bash", "-lc"]
    assert a[i + 3].endswith(cmd)                     # Befehl unverändert, als genau ein Argument am Ende
    assert len(a) == i + 4
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
    kills = [c for c in fake_incus["calls"] if c["args"][:2] == ["incus", "exec"] and "pkill" in c["args"]]
    assert kills and any(f"HH_EXEC_ID={exec_id}" in " ".join(k["args"]) for k in kills)


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
    assert any("pkill" in c["args"] for c in fake_incus["calls"])


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


# --- Werkzeuge in Container-Projekten ------------------------------------------------------------------------------

_CT = {"id": "p", "mcp_server_ids": [], "allowed_plugins": [],
       "execution": {"mode": "container", "container": "hh-labor-probe", "workdir": "/work", "user": 1000}}


def test_nur_die_erlaubten_werkzeuge():
    from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED, scope_tools
    tools = ["shell_exec", "file_read", "file_write", "file_patch", "todo_write", "load_skill", "web_search",
             "web_browser", "webmin_status", "webmin_call", "ask_agent", "send_mail", "generate_image",
             "datamining_search", "plugin__git-stats__git_commits", "create_specialist", "fetch_url"]
    local, mcp = scope_tools(_CT, tools, ["m1", "m2"])
    assert local == [t for t in tools if t in CONTAINER_ALLOWED]
    assert mcp == []
    for t in ("web_browser", "webmin_status", "ask_agent", "send_mail", "plugin__git-stats__git_commits"):
        assert t not in local


def test_erlaubte_liste_genau_wie_in_der_spec():
    from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED
    assert set(CONTAINER_ALLOWED) == {"shell_exec", "file_read", "file_write", "file_patch", "todo_write",
                                      "load_skill", "list_skills", "web_search", "fetch_url", "help_read",
                                      "help_search", "read_memory", "write_memory", "search_memory"}


def test_host_projekt_unveraendert():
    from hydrahive.runner._project_tool_scope import scope_tools
    tools = ["shell_exec", "web_browser", "plugin__git-stats__git_commits"]
    assert scope_tools({"id": "p", "mcp_server_ids": [], "allowed_plugins": []}, tools, ["m1"]) == (tools, ["m1"])


def test_kaputte_ausfuehrung_ergibt_keine_werkzeuge():
    from hydrahive.runner._project_tool_scope import scope_tools
    broken = {**_CT, "execution": {"mode": "container", "container": "X;y"}}
    assert scope_tools(broken, ["shell_exec", "file_read", "web_search"], ["m1"]) == ([], [])
