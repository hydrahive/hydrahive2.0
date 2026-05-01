from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _runx(cwd: Path, *args: str, env: dict | None = None, timeout: int = 60) -> tuple[bool, str, str]:
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=str(cwd),
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)


def _inject_token(url: str, token: str | None) -> str:
    if not token or not url.startswith("https://"):
        return url
    return re.sub(r"^https://", f"https://x-access-token:{token}@", url, count=1)


def _author_env(repo_path: Path, author_name: str, author_email: str) -> dict:
    return {
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
        "HOME": str(repo_path),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "GIT_TERMINAL_PROMPT": "0",
    }


def clone_into(workspace: Path, repo_name: str, url: str, branch: str | None = None,
               token: str | None = None) -> tuple[bool, str]:
    """Klonen in `workspace/<repo_name>/`. Workspace muss existieren, Subdir
    darf noch nicht existieren."""
    target = workspace / repo_name
    if target.exists():
        return False, "repo_exists"
    workspace.mkdir(parents=True, exist_ok=True)
    auth_url = _inject_token(url, token)
    args = ["clone", "--quiet"]
    if branch:
        args += ["--branch", branch]
    args += [auth_url, str(target)]
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    ok, _, err = _runx(workspace, *args, env=env, timeout=120)
    if not ok:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        return False, err
    if token:
        _runx(target, "remote", "set-url", "origin", url)
    return True, ""


def set_remote(repo_path: Path, url: str) -> tuple[bool, str]:
    if not (repo_path / ".git").exists():
        return False, "no_repo"
    existing_ok, _, _ = _runx(repo_path, "remote", "get-url", "origin")
    if existing_ok:
        ok, _, err = _runx(repo_path, "remote", "set-url", "origin", url)
    else:
        ok, _, err = _runx(repo_path, "remote", "add", "origin", url)
    return ok, err


def commit_all(repo_path: Path, message: str, author_name: str, author_email: str) -> tuple[bool, str]:
    if not message.strip():
        return False, "empty_message"
    env = _author_env(repo_path, author_name, author_email)
    add_ok, _, add_err = _runx(repo_path, "add", "-A", env=env)
    if not add_ok:
        return False, add_err
    status_ok, status_out, _ = _runx(repo_path, "status", "--porcelain", env=env)
    if not status_ok or not status_out.strip():
        return False, "no_changes"
    ok, _, err = _runx(repo_path, "commit", "-m", message, env=env, timeout=30)
    return ok, err


def _remote_url(repo_path: Path) -> str:
    ok, out, _ = _runx(repo_path, "remote", "get-url", "origin")
    return out if ok else ""


def push(repo_path: Path, branch: str | None = None, token: str | None = None) -> tuple[bool, str]:
    remote_url = _remote_url(repo_path)
    if not remote_url:
        return False, "no_remote"
    auth_url = _inject_token(remote_url, token)
    branch_ok, branch_out, _ = _runx(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    target = branch or (branch_out if branch_ok else "HEAD")
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    ok, _, err = _runx(repo_path, "push", "--set-upstream", auth_url, target, env=env, timeout=120)
    return ok, err


def pull(repo_path: Path, branch: str | None = None, token: str | None = None) -> tuple[bool, str]:
    remote_url = _remote_url(repo_path)
    if not remote_url:
        return False, "no_remote"
    auth_url = _inject_token(remote_url, token)
    branch_ok, branch_out, _ = _runx(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    target = branch or (branch_out if branch_ok else "HEAD")
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    ok, _, err = _runx(repo_path, "pull", auth_url, target, env=env, timeout=120)
    return ok, err
