from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Workspace-Layout:
#   workspace/<repo-name>/.git/   ← Standard ab Multi-Repo-Umstellung
#   workspace/.git/               ← Legacy single-repo, wird als "_root" exposed
ROOT_REPO = "_root"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")


def _run(cwd: Path, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=str(cwd),
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def init_repo(repo_path: Path) -> bool:
    repo_path.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "init", "-q"], cwd=str(repo_path), check=True, timeout=10
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("git init in %s fehlgeschlagen: %s", repo_path, e)
        return False


def is_valid_name(name: str) -> bool:
    return name == ROOT_REPO or bool(NAME_RE.match(name))


def repo_path_for(workspace: Path, repo_name: str) -> Path | None:
    if not is_valid_name(repo_name):
        return None
    if repo_name == ROOT_REPO:
        return workspace
    return workspace / repo_name


def repo_status(repo_path: Path) -> dict:
    branch = _run(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        return {"initialized": False}

    remote_url = _run(repo_path, "remote", "get-url", "origin")

    ahead = behind = 0
    tracking = _run(repo_path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if tracking:
        ab = _run(repo_path, "rev-list", "--left-right", "--count", f"HEAD...{tracking}")
        parts = ab.split()
        if len(parts) == 2:
            try:
                ahead, behind = int(parts[0]), int(parts[1])
            except ValueError:
                pass

    log_raw = _run(repo_path, "log", "--format=%H|%s|%an|%ar", "-5")
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


def list_repos(workspace: Path) -> list[dict]:
    """Liefert eine Liste {name, status} für alle Repos im Workspace.

    Subdirs mit `.git/` werden nach Name sortiert. Wenn `workspace/.git/`
    existiert, wird zusätzlich ein implizites Legacy-Repo `_root` aufgeführt.
    """
    if not workspace.exists():
        return []
    out: list[dict] = []
    if (workspace / ".git").exists():
        out.append({"name": ROOT_REPO, "status": repo_status(workspace)})
    for child in sorted(workspace.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / ".git").exists():
            out.append({"name": child.name, "status": repo_status(child)})
    return out
