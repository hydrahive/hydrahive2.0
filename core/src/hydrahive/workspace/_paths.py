from __future__ import annotations
from pathlib import Path


class WorkspacePathError(Exception):
    """Pfad liegt ausserhalb des erlaubten Workspace."""


def resolve_in_workspace(root: Path, rel: str) -> Path:
    """Löst `rel` relativ zu `root` auf und stellt sicher, dass das Ergebnis
    innerhalb von `root` bleibt. Schützt gegen `..`-Traversal, absolute Pfade
    und Symlink-Ausbrüche (via `resolve()`).
    """
    if rel.startswith("/") or rel.startswith("\\"):
        raise WorkspacePathError(f"Absolute Pfade nicht erlaubt: {rel}")
    root_resolved = root.resolve()
    candidate = (root_resolved / rel).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise WorkspacePathError(f"Pfad ausserhalb des Workspace: {rel}")
    return candidate
