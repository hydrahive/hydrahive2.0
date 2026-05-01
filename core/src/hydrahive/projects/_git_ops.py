from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _runx(workspace: Path, *args: str, env: dict | None = None, timeout: int = 60) -> tuple[bool, str, str]:
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=str(workspace),
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)


def _inject_token(url: str, token: str | None) -> str:
    """Bei HTTPS-URLs Token als x-access-token einbauen — nur für eine Operation,
    wird nicht persistiert in remote.url damit `git remote -v` ihn nicht zeigt."""
    if not token or not url.startswith("https://"):
        return url
    return re.sub(r"^https://", f"https://x-access-token:{token}@", url, count=1)


def _author_env(workspace: Path, author_name: str, author_email: str) -> dict:
    return {
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
        "HOME": str(workspace),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "GIT_TERMINAL_PROMPT": "0",
    }


def clone_repo(workspace: Path, url: str, branch: str | None = None, token: str | None = None) -> tuple[bool, str]:
    if any(workspace.iterdir()):
        return False, "workspace_not_empty"
    auth_url = _inject_token(url, token)
    args = ["clone", "--quiet"]
    if branch:
        args += ["--branch", branch]
    args += [auth_url, str(workspace)]
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    ok, _, err = _runx(workspace.parent, *args, env=env, timeout=120)
    if not ok:
        return False, err
    if token:
        _runx(workspace, "remote", "set-url", "origin", url)
    return True, ""


def set_remote(workspace: Path, url: str) -> tuple[bool, str]:
    existing_ok, _, _ = _runx(workspace, "remote", "get-url", "origin")
    if existing_ok:
        ok, _, err = _runx(workspace, "remote", "set-url", "origin", url)
    else:
        ok, _, err = _runx(workspace, "remote", "add", "origin", url)
    return ok, err


def commit_all(workspace: Path, message: str, author_name: str, author_email: str) -> tuple[bool, str]:
    if not message.strip():
        return False, "empty_message"
    env = _author_env(workspace, author_name, author_email)
    add_ok, _, add_err = _runx(workspace, "add", "-A", env=env)
    if not add_ok:
        return False, add_err
    status_ok, status_out, _ = _runx(workspace, "status", "--porcelain", env=env)
    if not status_ok or not status_out.strip():
        return False, "no_changes"
    ok, _, err = _runx(workspace, "commit", "-m", message, env=env, timeout=30)
    return ok, err


def _remote_url(workspace: Path) -> str:
    ok, out, _ = _runx(workspace, "remote", "get-url", "origin")
    return out if ok else ""


def push(workspace: Path, branch: str | None = None, token: str | None = None) -> tuple[bool, str]:
    remote_url = _remote_url(workspace)
    if not remote_url:
        return False, "no_remote"
    auth_url = _inject_token(remote_url, token)
    branch_ok, branch_out, _ = _runx(workspace, "rev-parse", "--abbrev-ref", "HEAD")
    target = branch or (branch_out if branch_ok else "HEAD")
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    ok, _, err = _runx(workspace, "push", "--set-upstream", auth_url, target, env=env, timeout=120)
    return ok, err


def pull(workspace: Path, branch: str | None = None, token: str | None = None) -> tuple[bool, str]:
    remote_url = _remote_url(workspace)
    if not remote_url:
        return False, "no_remote"
    auth_url = _inject_token(remote_url, token)
    branch_ok, branch_out, _ = _runx(workspace, "rev-parse", "--abbrev-ref", "HEAD")
    target = branch or (branch_out if branch_ok else "HEAD")
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    ok, _, err = _runx(workspace, "pull", auth_url, target, env=env, timeout=120)
    return ok, err
