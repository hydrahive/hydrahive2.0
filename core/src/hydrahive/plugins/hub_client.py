"""Plugin-Hub-Client: spiegelt das Hub-Repo als lokalen Cache.

Der Cache liegt in `settings.plugin_hub_cache`. `refresh()` legt ihn beim
ersten Aufruf an (`git clone --depth=1 --filter=blob:none`) oder updated
ihn (`git pull`). `read_hub_index()` liefert den geparsten hub.json.

Privates Hub-Repo wird per SSH-URL geklont — der Service-User braucht
einen passenden SSH-Key bei GitHub. Anderer Repo-Stand: env
`HH_PLUGIN_HUB_GIT_URL` setzen.
"""
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
    cache = settings.plugin_hub_cache
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
        settings.plugin_hub_git_url, str(cache),
    ])
    if result.returncode != 0:
        raise HubError(f"git clone failed: {result.stderr.strip()}")


def read_hub_index() -> dict:
    """`hub.json` aus dem Cache lesen. Ruft refresh() bei Bedarf auf."""
    cache = settings.plugin_hub_cache
    if not (cache / "hub.json").exists():
        refresh()
    try:
        return json.loads((cache / "hub.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HubError(f"hub.json nicht lesbar: {e}") from e


def plugin_source_path(plugin_path: str) -> Path:
    """Absoluter Pfad eines Plugin-Source-Verzeichnisses im Cache."""
    cache = settings.plugin_hub_cache
    # Sicherheits-Check: kein Path-Escape ausm Cache
    full = (cache / plugin_path).resolve()
    if not str(full).startswith(str(cache.resolve())):
        raise HubError(f"ungültiger plugin-path: {plugin_path}")
    return full
