"""Modul-Hub-Client: spiegelt das Hub-Repo als lokalen Cache (Muster plugins/hub_client.py)."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_GIT_TIMEOUT = 60


class HubError(RuntimeError):
    """Hub-Repo nicht erreichbar oder kaputt."""


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
        timeout=_GIT_TIMEOUT, check=False,
    )


def refresh() -> None:
    """Sicherstellt, dass der Cache aktuell ist. Idempotent."""
    cache = settings.module_hub_cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    if (cache / ".git").exists():
        result = _run_git(["pull", "--ff-only"], cwd=cache)
        if result.returncode != 0:
            raise HubError(f"git pull failed: {result.stderr.strip()}")
        return
    if cache.exists():
        # Verzeichnis ohne .git — fragwürdiger Zustand, lieber neu anlegen
        import shutil
        shutil.rmtree(cache)
    result = _run_git([
        "clone", "--depth=1", "--filter=blob:none",
        settings.module_hub_git_url, str(cache),
    ])
    if result.returncode != 0:
        raise HubError(f"git clone failed: {result.stderr.strip()}")


def read_hub_index() -> dict:
    """`hub.json` aus dem Cache lesen. Ruft refresh() bei Bedarf auf."""
    cache = settings.module_hub_cache
    if not (cache / "hub.json").exists():
        refresh()
    try:
        return json.loads((cache / "hub.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HubError(f"hub.json nicht lesbar: {e}") from e


def module_source_path(module_path: str) -> Path:
    """Absoluter Pfad eines Modul-Source-Verzeichnisses im Cache."""
    cache_root = settings.module_hub_cache.resolve()
    full = (cache_root / module_path).resolve()
    try:
        full.relative_to(cache_root)  # echte Verzeichnis-Grenze, kein String-Prefix
    except ValueError as e:
        raise HubError(f"ungültiger module-path: {module_path}") from e
    return full
