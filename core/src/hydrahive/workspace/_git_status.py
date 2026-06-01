from __future__ import annotations
import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, timeout=15,
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "git_error")
    return res.stdout


def is_repo(root: Path) -> bool:
    return (root / ".git").exists()


def status(root: Path) -> dict:
    if not is_repo(root):
        return {"is_repo": False, "branch": None, "files": []}
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    out = _git(root, "status", "--porcelain")
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        code, name = line[:2], line[3:]
        # staged = Index-Spalte (erstes Zeichen) ist gesetzt und kein "?"
        staged = code[0] not in (" ", "?")
        files.append({"status": code.strip(), "path": name, "staged": staged})
    return {"is_repo": True, "branch": branch, "files": files}


def diff(root: Path, file: str) -> str:
    return _git(root, "diff", "HEAD", "--", file)


def stage(root: Path, file: str, staged: bool) -> None:
    if staged:
        _git(root, "add", "--", file)
    else:
        _git(root, "reset", "HEAD", "--", file)


def commit(root: Path, message: str) -> str:
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").strip()
