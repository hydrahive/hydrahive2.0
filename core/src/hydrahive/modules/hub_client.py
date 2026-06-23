"""Modul-Hub-Client — spiegelt EINE oder MEHRERE Hub-Repos als lokalen Cache.

Multi-Hub: der primäre Hub (`settings.module_hub_git_url`, Default GitHub) liegt
weiter im `settings.module_hub_cache`; zusätzliche Hubs (`module_hub_extra_git_urls`,
z.B. interne Gitea) klonen in Geschwister-Ordner `…/hub-<slug>`. `read_hub_index()`
merged die `hub.json`-Indizes (erste id gewinnt, jeder Eintrag mit `_hub` getaggt);
`module_source_path()` löst pro Hub auf. Per-Hub-Fehler beim Refresh sind isoliert.
"""
from __future__ import annotations

import json
import logging
import re
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
    primary_cache = settings.module_hub_cache
    hubs: list[tuple[str | None, str, Path]] = [
        (None, settings.module_hub_git_url, primary_cache)
    ]
    for url in settings.module_hub_extra_git_urls:
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
            # ff-only schlägt fehl, wenn die Hub-History divergiert (z.B. nach
            # einem force-push/History-Rewrite im Hub-Repo). Der Cache ist eine
            # REINE Spiegelung ohne lokale Commits — es gibt nichts zu verlieren.
            # Statt das Update für den Nutzer zu blockieren (der keine Shell hat),
            # hart auf den Remote-Stand re-synchronisieren. Selbstheilend.
            _resync_hard(cache, result.stderr.strip())
        return
    if cache.exists():
        import shutil
        shutil.rmtree(cache)
    result = _run_git(["clone", "--depth=1", "--filter=blob:none", url, str(cache)])
    if result.returncode != 0:
        raise HubError(f"git clone failed: {result.stderr.strip()}")


def _resync_hard(cache: Path, pull_error: str) -> None:
    """Hub-Cache hart auf den Remote-Stand zwingen (Fallback bei divergierter
    History). Sicher, weil der Cache nur gespiegelt wird — keine lokale Arbeit.

    Ermittelt den aktuellen Branch des Caches und setzt ihn auf origin/<branch>.
    """
    logger.warning("Hub pull --ff-only fehlgeschlagen, re-sync hart auf Remote: %s", pull_error)
    fetched = _run_git(["fetch", "origin"], cwd=cache)
    if fetched.returncode != 0:
        raise HubError(f"git fetch failed: {fetched.stderr.strip()}")
    head = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cache).stdout.strip() or "main"
    reset = _run_git(["reset", "--hard", f"origin/{head}"], cwd=cache)
    if reset.returncode != 0:
        raise HubError(f"git reset failed: {reset.stderr.strip()}")


def refresh() -> None:
    """Alle Hubs best-effort aktualisieren — Per-Hub-Fehler isoliert (geloggt).

    Ein nicht erreichbarer Hub (z.B. GitHub offline) darf die anderen nicht
    blockieren. read_hub_index() listet danach, was an Cache vorhanden ist.
    """
    for name, url, cache in _hubs():
        try:
            _refresh_one(cache, url)
        except HubError as e:
            logger.warning("Hub-Refresh fehlgeschlagen (%s): %s", name or "default", e)


def _read_one(cache: Path) -> dict:
    f = cache / "hub.json"
    if not f.exists():
        return {"modules": []}
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
    modules: list[dict] = []
    seen: set[str] = set()
    for name, _url, cache in hubs:
        for m in _read_one(cache).get("modules", []):
            mid = m.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            modules.append({**m, "_hub": name})
    return {"modules": modules}


def _cache_for_hub(hub_name: str | None) -> Path:
    for name, _url, cache in _hubs():
        if name == hub_name:
            return cache
    raise HubError(f"unbekannter hub: {hub_name!r}")


def module_source_path(module_path: str, hub_name: str | None = None) -> Path:
    """Absoluter Pfad eines Modul-Source-Verzeichnisses im (passenden) Hub-Cache."""
    cache_root = _cache_for_hub(hub_name).resolve()
    full = (cache_root / module_path).resolve()
    try:
        full.relative_to(cache_root)  # echte Verzeichnis-Grenze, kein String-Prefix
    except ValueError as e:
        raise HubError(f"ungültiger module-path: {module_path}") from e
    return full
