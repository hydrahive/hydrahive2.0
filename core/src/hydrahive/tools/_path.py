from __future__ import annotations

from pathlib import Path


class PathOutsideWorkspace(ValueError):
    """Raised when a path resolves outside the agent's workspace."""


def safe_path(workspace: Path, requested: str) -> Path:
    """Resolve `requested` and ensure it stays inside `workspace`.

    Accepts both absolute and relative paths. Relative paths are resolved
    against the workspace. The resolved path must equal the workspace or
    be a descendant — symlinks are followed via `.resolve()`.
    """
    if not requested:
        raise PathOutsideWorkspace("Leerer Pfad")

    workspace = workspace.resolve()
    p = Path(requested)
    if not p.is_absolute():
        p = workspace / p
    p = p.resolve()

    if p == workspace:
        return p
    try:
        p.relative_to(workspace)
    except ValueError:
        raise PathOutsideWorkspace(f"Pfad außerhalb Workspace: {requested}")
    return p
