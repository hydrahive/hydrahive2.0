"""graphify-Installation für den Code-Graph.

graphify läuft in einem isolierten venv unter $HH_DATA_DIR/tools/graphify/venv
(nicht im HydraHive-venv). Angelegt wird es beim ersten Bauen oder vorab vom
Installer (installer/lib/graphify.sh), damit der erste Build nicht minutenlang
auf pip wartet.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hydrahive.settings import settings


class CodeGraphError(RuntimeError):
    pass


def _venv_dir() -> Path:
    return settings.data_dir / "tools" / "graphify" / "venv"


def _graphify_bin() -> Path:
    return _venv_dir() / "bin" / "graphify"


def _venv_minor(venv: Path) -> tuple[int, int] | None:
    """Python-Version des venv laut pyvenv.cfg (`python -m venv` schreibt `version`, uv `version_info`)."""
    try:
        lines = (venv / "pyvenv.cfg").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        key, _, value = line.partition("=")
        if key.strip() in ("version", "version_info"):
            parts = value.strip().split(".")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return int(parts[0]), int(parts[1])
    return None


def _is_installed() -> bool:
    """graphify da, Interpreter vorhanden und gleiche Python-Version wie HydraHive.

    Nach einem Python-Wechsel (Ubuntu 26.04: 3.12 → 3.14) zeigt bin/python
    ins Leere oder auf die alte Version — dann neu bauen (Spec python-314-umstieg).
    Ohne Unterprozess: läuft bei jeder Status-Abfrage der Oberfläche.
    """
    venv = _venv_dir()
    python = venv / "bin" / "python"
    return (
        _graphify_bin().is_file()
        and python.exists()  # folgt dem Symlink: entfernter Interpreter → False
        and _venv_minor(venv) == sys.version_info[:2]
    )


def bootstrap_status() -> dict:
    return {"installed": _is_installed()}


def ensure_installed() -> None:
    """Legt das isolierte venv an und installiert graphify (idempotent).

    --clear: ein vorhandenes, aber veraltetes venv wird vollständig ersetzt.
    """
    if _is_installed():
        return
    venv = _venv_dir()
    venv.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", "--clear", str(venv)], check=True, capture_output=True, timeout=120,
        )
        subprocess.run(
            [str(venv / "bin" / "pip"), "install", "--quiet", "graphifyy"],
            check=True, capture_output=True, timeout=600,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise CodeGraphError("graphify-Installation fehlgeschlagen") from exc
    if not _graphify_bin().is_file():
        raise CodeGraphError("graphify-Binary nach Installation nicht gefunden")
