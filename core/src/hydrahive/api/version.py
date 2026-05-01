"""Git-Commit + Update-Behind-Status für /api/health.

Liest Repo-Stand via subprocess (read-only, kein .git-Schreibzugriff) damit
ProtectSystem=strict in der systemd-Unit nicht stört.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _detect_git_commit() -> str | None:
    if not (_REPO_ROOT / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _remote_url_https() -> str | None:
    """Gibt die Remote-URL zurück, SSH-URLs werden auf HTTPS umgebogen.

    git@github.com:org/repo.git → https://github.com/org/repo.git
    Der hydrahive-User hat keine SSH-Keys — HTTPS funktioniert für public Repos immer.
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        url = r.stdout.strip()
        if not url:
            return None
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):]
        return url
    except Exception:
        return None


def _check_update_behind() -> int | None:
    """0 wenn HEAD == origin/main, 1 wenn behind, None wenn nicht detectierbar."""
    if not (_REPO_ROOT / ".git").exists():
        return None
    try:
        remote_url = _remote_url_https()
        if not remote_url:
            return None
        ls = subprocess.run(
            ["git", "ls-remote", remote_url, "refs/heads/main"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if ls.returncode != 0 or not ls.stdout.strip():
            return None
        remote_sha = ls.stdout.split()[0]
        head = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if head.returncode != 0:
            return None
        return 0 if head.stdout.strip() == remote_sha else 1
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


_GIT_COMMIT: str | None = _detect_git_commit()
_UPDATE_BEHIND: int | None = None


async def update_check_loop() -> None:
    """Background-Task: refreshed Commit + Update-Behind alle 30 Min."""
    global _UPDATE_BEHIND, _GIT_COMMIT
    while True:
        try:
            _GIT_COMMIT = await asyncio.to_thread(_detect_git_commit)
            _UPDATE_BEHIND = await asyncio.to_thread(_check_update_behind)
        except Exception as e:
            logger.warning("Update-Check fehlgeschlagen: %s", e)
        await asyncio.sleep(1800)


async def refresh_update_status() -> tuple[str | None, int | None]:
    """On-Demand-Refresh — System-Page kann sofort einen frischen Stand holen."""
    global _UPDATE_BEHIND, _GIT_COMMIT
    _GIT_COMMIT = await asyncio.to_thread(_detect_git_commit)
    _UPDATE_BEHIND = await asyncio.to_thread(_check_update_behind)
    return _GIT_COMMIT, _UPDATE_BEHIND


def current_status() -> tuple[str | None, int | None]:
    return _GIT_COMMIT, _UPDATE_BEHIND
