"""Theme-Hub-Client — spiegelt EIN oder MEHRERE Hub-Repos als lokalen Cache.

Direkte Spiegelung des Modul-Hub-Clients (hydrahive.modules.hub_client), nur auf
Themes gemünzt: primärer Hub `settings.theme_hub_git_url` (GitHub), zusätzliche
Hubs via `theme_hub_extra_git_urls` klonen in Geschwister-Ordner `…/hub-<slug>`.
`read_hub_index()` merged die `hub.json`-Indizes (erste id gewinnt, jeder Eintrag
mit `_hub` getaggt); `theme_source_path()` löst pro Hub auf. Per-Hub-Fehler beim
Refresh sind isoliert.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_GIT_TIMEOUT = 60


class HubError(RuntimeError):
    """Hub-Repo nicht erreichbar oder kaputt."""


def _slug(url: str) -> str:
    s = re.sub(r"^[a-z]+://", "", url.lower())
    s = re.sub(r"\.git$", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "hub"


def _hubs() -> list[tuple[str | None, str, Path]]:
    """(name, git_url, cache_dir). name=None → primärer Hub (Default-GitHub)."""
    primary_cache = settings.theme_hub_cache
    hubs: list[tuple[str | None, str, Path]] = [
        (None, settings.theme_hub_git_url, primary_cache)
    ]
    for url in settings.theme_hub_extra_git_urls:
        hubs.append((_slug(url), url, primary_cache.parent / f"hub-{_slug(url)}"))
    return hubs


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
        timeout=_GIT_TIMEOUT, check=False,
    )


def _refresh_one(cache: Path, url: str) -> None:
    """Einen Hub klonen/pullen. Idempotent."""
    cache.parent.mkdir(parents=True, exist_ok=True)
    if (cache / ".git").exists():
        result = _run_git(["pull", "--ff-only"], cwd=cache)
        if result.returncode != 0:
            # ff-only scheitert bei divergierter Hub-History. Der Cache ist eine
            # reine Spiegelung ohne lokale Commits — hart auf Remote re-syncen.
            _resync_hard(cache, result.stderr.strip())
        return
    if cache.exists():
        shutil.rmtree(cache)
    result = _run_git(["clone", "--depth=1", "--filter=blob:none", url, str(cache)])
    if result.returncode != 0:
        raise HubError(f"git clone failed: {result.stderr.strip()}")


def _resync_hard(cache: Path, pull_error: str) -> None:
    """Hub-Cache hart auf Remote zwingen (Fallback bei divergierter History).
    Sicher, weil der Cache nur gespiegelt wird — keine lokale Arbeit.
    """
    logger.warning("Theme-Hub pull --ff-only fehlgeschlagen, re-sync hart: %s", pull_error)
    fetched = _run_git(["fetch", "origin"], cwd=cache)
    if fetched.returncode != 0:
        raise HubError(f"git fetch failed: {fetched.stderr.strip()}")
    head = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cache).stdout.strip() or "main"
    reset = _run_git(["reset", "--hard", f"origin/{head}"], cwd=cache)
    if reset.returncode != 0:
        raise HubError(f"git reset failed: {reset.stderr.strip()}")


def refresh() -> None:
    """Alle Hubs best-effort aktualisieren — Per-Hub-Fehler isoliert (geloggt)."""
    for name, url, cache in _hubs():
        try:
            _refresh_one(cache, url)
        except HubError as e:
            logger.warning("Theme-Hub-Refresh fehlgeschlagen (%s): %s", name or "default", e)


def _read_one(cache: Path) -> dict:
    f = cache / "hub.json"
    if not f.exists():
        return {"themes": []}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HubError(f"hub.json nicht lesbar: {e}") from e


def read_hub_index() -> dict:
    """Gemergter `hub.json`-Index über alle Hubs. Erste id gewinnt; `_hub`-Tag
    nennt die Quelle (None = primär). Refresh nur wenn noch GAR kein Cache da ist.
    """
    hubs = _hubs()
    if not any((cache / "hub.json").exists() for _, _, cache in hubs):
        refresh()
    themes: list[dict] = []
    seen: set[str] = set()
    for name, _url, cache in hubs:
        for th in _read_one(cache).get("themes", []):
            tid = th.get("id")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            themes.append({**th, "_hub": name})
    return {"themes": themes}


def _cache_for_hub(hub_name: str | None) -> Path:
    for name, _url, cache in _hubs():
        if name == hub_name:
            return cache
    raise HubError(f"unbekannter hub: {hub_name!r}")


def theme_source_path(theme_path: str, hub_name: str | None = None) -> Path:
    """Absoluter Pfad eines Theme-Source-Verzeichnisses im (passenden) Hub-Cache."""
    cache_root = _cache_for_hub(hub_name).resolve()
    full = (cache_root / theme_path).resolve()
    try:
        full.relative_to(cache_root)  # echte Verzeichnis-Grenze, kein String-Prefix
    except ValueError as e:
        raise HubError(f"ungültiger theme-path: {theme_path}") from e
    return full
