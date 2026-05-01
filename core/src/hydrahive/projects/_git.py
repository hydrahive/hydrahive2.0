from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _run(workspace: Path, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=str(workspace),
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def init_repo(workspace: Path) -> bool:
    try:
        subprocess.run(
            ["git", "init", "-q"], cwd=str(workspace), check=True, timeout=10
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("git init in %s fehlgeschlagen: %s", workspace, e)
        return False


def git_status(workspace: Path) -> dict:
    branch = _run(workspace, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        return {"initialized": False}

    remote_url = _run(workspace, "remote", "get-url", "origin")

    ahead = behind = 0
    tracking = _run(workspace, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if tracking:
        ab = _run(workspace, "rev-list", "--left-right", "--count", f"HEAD...{tracking}")
        parts = ab.split()
        if len(parts) == 2:
            try:
                ahead, behind = int(parts[0]), int(parts[1])
            except ValueError:
                pass

    log_raw = _run(workspace, "log", "--format=%H|%s|%an|%ar", "-5")
    commits = []
    for line in log_raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0][:8],
                "subject": parts[1],
                "author": parts[2],
                "date": parts[3],
            })

    return {
        "initialized": True,
        "branch": branch,
        "remote_url": remote_url or None,
        "ahead": ahead,
        "behind": behind,
        "commits": commits,
    }
