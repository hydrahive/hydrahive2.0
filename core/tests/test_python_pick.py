"""Interpreterwahl der Installer (Spec docs/specs/python-314-umstieg.md).

Regel: das System-Python der Distribution (`python3`), aufgelöst auf die
versionierte Datei, sofern mindestens 3.12. Nur wenn das zu alt ist, ein
nachinstalliertes 3.13/3.12 (z. B. deadsnakes auf 22.04).

Anlass: Prod (Ubuntu 26.04, python3 = 3.14) lief weiter auf einem 3.12 aus
alten 24.04-Paketen, weil die Installer 3.12 fest bevorzugten. Ein
`apt autoremove` hätte HydraHive lahmgelegt.

Die Interpreter sind hier Attrappen, die nur ihre Version melden — der
Helfer fragt die Version über `hh_python_minor` ab.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "installer" / "lib" / "python-venv.sh"
DEPS = REPO_ROOT / "installer" / "modules" / "00-deps.sh"


def _fake_python(bin_dir: Path, name: str, version: str) -> Path:
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\necho {version}\n")
    path.chmod(0o755)
    return path


def _pick(bin_dir: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "HH_PYTHON_BIN_DIR": str(bin_dir),
        **extra,
    }
    return subprocess.run(
        ["bash", "-c", 'set -euo pipefail; source "$1"; hh_pick_python', "pick", str(HELPER)],
        capture_output=True, text=True, env=env,
    )


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    d = tmp_path / "bin"
    d.mkdir()
    return d


def test_prod_case_system_python_wins_over_leftover_312(bin_dir: Path) -> None:
    """Ubuntu 26.04 mit übrig gebliebenem 3.12: gewählt wird 3.14, aufgelöst."""
    _fake_python(bin_dir, "python3.14", "3.14")
    _fake_python(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.14")

    result = _pick(bin_dir)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(bin_dir / "python3.14")


def test_ubuntu_2404_keeps_312(bin_dir: Path) -> None:
    _fake_python(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.12")

    assert _pick(bin_dir).stdout.strip() == str(bin_dir / "python3.12")


def test_too_old_system_python_falls_back_to_deadsnakes(bin_dir: Path) -> None:
    """Ubuntu 22.04: python3 ist 3.10, 3.12 kommt aus deadsnakes."""
    _fake_python(bin_dir, "python3.10", "3.10")
    _fake_python(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.10")

    assert _pick(bin_dir).stdout.strip() == str(bin_dir / "python3.12")


def test_311_is_no_longer_accepted(bin_dir: Path) -> None:
    """core verlangt >= 3.12 — ein venv mit 3.11 scheitert sonst erst bei pip."""
    _fake_python(bin_dir, "python3.10", "3.10")
    _fake_python(bin_dir, "python3.11", "3.11")
    (bin_dir / "python3").symlink_to("python3.10")

    result = _pick(bin_dir)

    assert result.returncode != 0
    assert "3.12" in result.stderr


def test_311_as_system_python_is_skipped(bin_dir: Path) -> None:
    """System-Python 3.11 (z. B. Debian 12): nicht nehmen, sondern 3.12 daneben."""
    _fake_python(bin_dir, "python3.11", "3.11")
    _fake_python(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.11")

    assert _pick(bin_dir).stdout.strip() == str(bin_dir / "python3.12")


def test_bin_dir_override_must_be_absolute(bin_dir: Path) -> None:
    result = _pick(Path("relativ/bin"))

    assert result.returncode != 0
    assert "absolut" in result.stderr


def test_explicit_override_still_wins(bin_dir: Path) -> None:
    _fake_python(bin_dir, "python3.14", "3.14")
    (bin_dir / "python3").symlink_to("python3.14")
    pinned = _fake_python(bin_dir, "python3.12", "3.12")

    assert _pick(bin_dir, HH_PYTHON=str(pinned)).stdout.strip() == str(pinned)


def test_deps_install_system_python_not_fixed_312() -> None:
    text = DEPS.read_text()
    packages = text.split("REQUIRED_PACKAGES=(", 1)[1].split(")", 1)[0].split()

    assert {"python3", "python3-venv", "python3-dev"} <= set(packages)
    assert not any(p.startswith("python3.12") for p in packages)


def test_deps_use_deadsnakes_only_when_system_python_too_old() -> None:
    text = DEPS.read_text()
    ppa = text.index("ppa:deadsnakes/ppa")
    guard = text.rindex("if ", 0, ppa)

    assert "sys.version_info >= (3, 12)" in text[guard:ppa]
    # Erst nach der Grundinstallation prüfen — auf frischen Images fehlt python3 sonst.
    assert text.index('apt-get install -y "${REQUIRED_PACKAGES[@]}"') < guard
