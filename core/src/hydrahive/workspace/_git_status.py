from __future__ import annotations
import subprocess
from pathlib import Path

ROOT_REPO = "_root"


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


def _branch(repo_path: Path) -> str | None:
    try:
        return _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except RuntimeError:
        return None


def list_repos(root: Path) -> list[dict]:
    """Repos im Workspace: Wurzel (als `_root`) + direkte Unterordner mit `.git`.
    Deckt HH2s Multi-Repo-Layout (`workspace/<repo>/.git`) und Legacy-Single-Repo ab."""
    if not root.exists():
        return []
    out: list[dict] = []
    if (root / ".git").exists():
        out.append({"name": ROOT_REPO, "branch": _branch(root)})
    for child in sorted(root.iterdir()):
        if child.is_dir() and not child.name.startswith(".") and (child / ".git").exists():
            out.append({"name": child.name, "branch": _branch(child)})
    return out


def resolve_repo(root: Path, repo: str) -> Path | None:
    """Repo-Name → Pfad. Nur tatsächlich existierende Repos (traversal-sicher,
    da nur gegen die gescannte Liste gematcht wird)."""
    for r in list_repos(root):
        if r["name"] == repo:
            return root if repo == ROOT_REPO else root / repo
    return None


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


MAX_DIFF_BYTES = 512 * 1024  # 512 KB — gegen OOM bei riesigen/Binär-Diffs


def diff(root: Path, file: str) -> str:
    out = _git(root, "diff", "HEAD", "--", file)
    if len(out) > MAX_DIFF_BYTES:
        return out[:MAX_DIFF_BYTES] + "\n[diff truncated]"
    return out


def stage(root: Path, file: str, staged: bool) -> None:
    if staged:
        _git(root, "add", "--", file)
    else:
        _git(root, "reset", "HEAD", "--", file)


def commit(root: Path, message: str) -> str:
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").strip()
