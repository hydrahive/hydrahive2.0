"""docs/specs/projekt-container-ausfuehrung.md (K1a): welcher Launcher – fail-closed, nie still auf den Server."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.tools import _launcher_container
from hydrahive.tools._launcher import DevLauncher, set_launcher
from hydrahive.tools.base import ToolContext


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


