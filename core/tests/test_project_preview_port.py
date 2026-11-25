"""Vorschau-Port je Projekt (ziele/projekt-testumgebung.md §3 Weg B, E1a): eindeutig, stabil, in shell_exec."""
from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest

from hydrahive.projects import config as project_config
from hydrahive.projects import preview_port
from hydrahive.tools import shell
from hydrahive.tools._launcher import LaunchResult, set_launcher
from hydrahive.tools._launcher_sandbox import sandbox_env
from hydrahive.tools.base import ToolContext


def _new_project(name: str = "Vorschau") -> str:
    created = project_config.create(name=name, description="", members=[], created_by="admin",
                                    template=None, llm_model="test/model")
    cfg = created[0] if isinstance(created, tuple) else created
    return cfg["id"]


@pytest.fixture
def fresh(setup_test_env, monkeypatch):
    """Eigener Bereich je Test, damit Projekte anderer Tests nicht stören."""
    from hydrahive.db import init_db
    init_db()
    monkeypatch.setenv("HH_PREVIEW_PORT_MIN", "28100")
    monkeypatch.setenv("HH_PREVIEW_PORT_MAX", "28102")
    for p in project_config.list_all():
        if p.get(preview_port.FIELD) is not None:
            project_config.update(p["id"], **{preview_port.FIELD: None})
    yield


def test_port_ist_stabil(fresh):
    pid = _new_project()
    first = preview_port.ensure(pid)
    assert preview_port.ensure(pid) == first
    assert project_config.get(pid)[preview_port.FIELD] == first        # in der Projekt-Konfig gespeichert


def test_ports_sind_eindeutig(fresh):
    ports = {preview_port.ensure(_new_project(f"P{i}")) for i in range(3)}
    assert ports == {28100, 28101, 28102}


def test_bereich_voll_meldet_fehler(fresh):
    for i in range(3):
        preview_port.ensure(_new_project(f"V{i}"))
    with pytest.raises(preview_port.PreviewPortError) as exc:
        preview_port.ensure(_new_project("zu viel"))
    assert exc.value.code == "preview_port_exhausted"


def test_doppelter_port_wird_neu_vergeben(fresh):
    a, b = _new_project("A"), _new_project("B")
    port_a = preview_port.ensure(a)
    project_config.update(b, **{preview_port.FIELD: port_a})          # z. B. kopierte Konfig
    assert preview_port.ensure(b) != port_a
    assert preview_port.ensure(a) == port_a


def test_port_ausserhalb_des_bereichs_wird_ersetzt(fresh):
    pid = _new_project()
    project_config.update(pid, **{preview_port.FIELD: 80})
    assert 28100 <= preview_port.ensure(pid) <= 28102


def test_ungueltiger_bereich_faellt_auf_standard(monkeypatch):
    monkeypatch.setenv("HH_PREVIEW_PORT_MIN", "30000")
    monkeypatch.setenv("HH_PREVIEW_PORT_MAX", "20000")
    assert preview_port.port_range() == (preview_port.DEFAULT_MIN, preview_port.DEFAULT_MAX)
    monkeypatch.setenv("HH_PREVIEW_PORT_MIN", "abc")
    monkeypatch.setenv("HH_PREVIEW_PORT_MAX", "22")
    assert preview_port.port_range() == (preview_port.DEFAULT_MIN, preview_port.DEFAULT_MAX)


def test_running_erkennt_offenen_port():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        assert preview_port.running(port) is True
    finally:
        srv.close()
    assert preview_port.running(port) is False


class _Fake:
    def __init__(self) -> None:
        self.env: dict = {}

    async def run(self, cmd: str, cwd: Path, timeout: int = 60, env: dict | None = None):
        self.env = env or {}
        return LaunchResult(exit_code=0, stdout="", stderr="")


@pytest.fixture
def fake_launcher():
    fake = _Fake()
    set_launcher(fake)
    yield fake
    from hydrahive.tools._launcher import DevLauncher
    set_launcher(DevLauncher())


def test_shell_exec_setzt_hh_preview_port(fresh, fake_launcher, tmp_path):
    pid = _new_project()
    ctx = ToolContext(session_id="s1", agent_id="", user_id="admin", workspace=tmp_path, project_id=pid)
    asyncio.run(shell._execute({"cmd": "echo $HH_PREVIEW_PORT"}, ctx))
    assert fake_launcher.env.get("HH_PREVIEW_PORT") == str(preview_port.ensure(pid))


def test_shell_exec_ohne_projekt_ohne_port(fresh, fake_launcher, tmp_path):
    ctx = ToolContext(session_id="s1", agent_id="", user_id="admin", workspace=tmp_path)
    asyncio.run(shell._execute({"cmd": "true"}, ctx))
    assert "HH_PREVIEW_PORT" not in fake_launcher.env


def test_sandbox_reicht_port_durch():
    assert sandbox_env({"HH_PREVIEW_PORT": "18123", "HH_SECRET_KEY": "x"}) == {
        "HH_PREVIEW_PORT": "18123", "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}


def test_container_launcher_bekommt_keine_server_umgebung():
    """Container-Weg (E2): nur feste Werte im Container, HH_PREVIEW_PORT gehört nicht dazu."""
    import inspect

    from hydrahive.tools._launcher_container import ContainerLauncher
    src = inspect.getsource(ContainerLauncher.run)
    assert "del cwd, env" in src and "HH_PREVIEW_PORT" not in src
