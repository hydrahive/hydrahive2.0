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
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to("/usr/bin/python3.12-entfernt")
    _fake_graphify(venv)

    assert cgi.bootstrap_status() == {"installed": False}


def test_venv_with_other_python_version_is_not_installed(venv: Path) -> None:
    (venv / "bin").mkdir(parents=True)
    other = venv / "bin" / "python"
    other.write_text("#!/bin/sh\necho 3.11\n")
    other.chmod(0o755)
    _fake_graphify(venv)

    assert cgi.bootstrap_status() == {"installed": False}


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
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cgi.subprocess, "run", fake_run)

    cgi.ensure_installed()

    assert calls[0][:4] == [sys.executable, "-m", "venv", "--clear"]
    assert calls[1][0] == str(venv / "bin" / "pip")


def test_installer_rebuilds_on_version_mismatch() -> None:
    text = GRAPHIFY_SH.read_text()
    guard = text.split('graphify für den Code-Graph installieren', 1)[0]

    # „vorhanden“ heißt: graphify da UND Interpreter-Version wie HydraHive.
    assert 'sys.version_info[:2]' in guard
    assert '-m venv --clear "$venv"' in text
