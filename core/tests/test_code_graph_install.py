"""graphify-venv folgt dem HydraHive-Python (Spec docs/specs/python-314-umstieg.md).

Prod: /var/lib/hydrahive2/tools/graphify/venv ist mit 3.12 gebaut. Als
„installiert“ galt bisher, dass bin/graphify existiert — auch wenn dessen
Interpreter längst fehlt. Nach dem Umstieg auf 3.14 und dem Entfernen von
3.12 wäre der Code-Graph dauerhaft kaputt, ohne dass ein Neubau anläuft.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from hydrahive import code_graph_install as cgi
from hydrahive.settings import settings

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPHIFY_SH = REPO_ROOT / "installer" / "lib" / "graphify.sh"


@pytest.fixture
def venv(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    return tmp_path / "data" / "tools" / "graphify" / "venv"


def _fake_graphify(venv: Path) -> None:
    (venv / "bin" / "graphify").write_text("#!/bin/sh\nexit 0\n")
    (venv / "bin" / "graphify").chmod(0o755)


def test_venv_with_vanished_interpreter_is_not_installed(venv: Path) -> None:
    """Version laut pyvenv.cfg passt, aber der Interpreter ist weg (Paket entfernt)."""
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to("/usr/bin/python3.12-entfernt")
    (venv / "pyvenv.cfg").write_text("version = %d.%d.0\n" % sys.version_info[:2])
    _fake_graphify(venv)

    assert cgi.bootstrap_status() == {"installed": False}


def test_venv_with_other_python_version_is_not_installed(venv: Path) -> None:
    """Prod heute: Interpreter 3.12 existiert noch, HydraHive läuft auf 3.14."""
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    cfg = venv / "pyvenv.cfg"
    cfg.write_text(
        "\n".join(
            "version = 3.11.9" if line.startswith(("version", "version_info")) else line
            for line in cfg.read_text().splitlines()
        )
        + "\n"
    )
    _fake_graphify(venv)

    assert cgi.bootstrap_status() == {"installed": False}


@pytest.mark.parametrize("key", ["version", "version_info"])
def test_reads_both_pyvenv_formats(venv: Path, key: str) -> None:
    """`python -m venv` schreibt `version`, uv schreibt `version_info`."""
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(sys.executable)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n%s = %d.%d.4\n" % (key, *sys.version_info[:2]))
    _fake_graphify(venv)

    assert cgi.bootstrap_status() == {"installed": True}


def test_status_does_not_spawn_processes(venv: Path, monkeypatch) -> None:
    """bootstrap_status läuft bei jeder Status-Abfrage der Oberfläche."""
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    _fake_graphify(venv)

    def forbidden(*args, **kwargs):
        raise AssertionError("kein Unterprozess im Status")

    monkeypatch.setattr(cgi.subprocess, "run", forbidden)

    assert cgi.bootstrap_status() == {"installed": True}


def test_matching_venv_is_installed(venv: Path) -> None:
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    _fake_graphify(venv)

    assert cgi.bootstrap_status() == {"installed": True}


def test_ensure_rebuilds_with_clear(venv: Path, monkeypatch) -> None:
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to("/usr/bin/python3.12-entfernt")
    _fake_graphify(venv)
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append([str(c) for c in cmd])
        if "venv" in cmd:
            (venv / "bin" / "python").unlink()
            (venv / "bin" / "python").symlink_to(sys.executable)
            (venv / "pyvenv.cfg").write_text("version_info = %d.%d.0\n" % sys.version_info[:2])
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cgi.subprocess, "run", fake_run)

    cgi.ensure_installed()

    assert calls[0][:4] == [sys.executable, "-m", "venv", "--clear"]
    assert calls[1][0] == str(venv / "bin" / "pip")


def _ensure_graphify_sh(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    """installer/lib/graphify.sh mit Attrappen für runuser/install und ohne Netz."""
    calls = tmp_path / "calls.log"
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    # runuser -u <user> -- <cmd…>: Aufruf nur protokollieren.
    (stubs / "runuser").write_text(f'#!/bin/sh\nshift 3\necho "$*" >> {calls}\n')
    (stubs / "install").write_text("#!/bin/sh\nexit 0\n")
    for s in stubs.iterdir():
        s.chmod(0o755)
    repo = tmp_path / "repo"
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "python").symlink_to(sys.executable)
    result = subprocess.run(
        ["bash", "-c", 'set -euo pipefail; source "$1"; ensure_graphify', "g", str(GRAPHIFY_SH)],
        capture_output=True, text=True,
        env={"PATH": f"{stubs}:/usr/bin:/bin", "HH_DATA_DIR": str(tmp_path / "data"),
             "HH_USER": "nobody", "HH_REPO_DIR": str(repo), "LANG": "C.UTF-8"},
    )
    return result, calls


def test_installer_rebuilds_venv_of_other_python_version(tmp_path: Path) -> None:
    """Prod heute: graphify da, venv-Python 3.12 läuft noch, Kern auf 3.14."""
    venv = tmp_path / "data" / "tools" / "graphify" / "venv"
    (venv / "bin").mkdir(parents=True)
    old = venv / "bin" / "python"
    old.write_text("#!/bin/sh\necho 3.11\n")
    old.chmod(0o755)
    _fake_graphify(venv)

    result, calls = _ensure_graphify_sh(tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"-m venv --clear {venv}" in calls.read_text()


def test_installer_keeps_matching_venv(tmp_path: Path) -> None:
    venv = tmp_path / "data" / "tools" / "graphify" / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(sys.executable)
    _fake_graphify(venv)

    result, calls = _ensure_graphify_sh(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "vorhanden" in result.stdout
    assert not calls.exists()
