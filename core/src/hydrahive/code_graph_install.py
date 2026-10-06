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


def bootstrap_status() -> dict:
    return {"installed": _graphify_bin().is_file()}


def ensure_installed() -> None:
    """Legt das isolierte venv an und installiert graphify (idempotent)."""
    if _graphify_bin().is_file():
        return
    venv = _venv_dir()
    venv.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True, timeout=120)
        subprocess.run(
            [str(venv / "bin" / "pip"), "install", "--quiet", "graphifyy"],
            check=True, capture_output=True, timeout=600,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise CodeGraphError("graphify-Installation fehlgeschlagen") from exc
    if not _graphify_bin().is_file():
        raise CodeGraphError("graphify-Binary nach Installation nicht gefunden")
