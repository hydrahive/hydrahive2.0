"""Code-Graph Konfiguration: Scan-Verzeichnisse pro Projekt + Validierung.

Getrennt von code_graph.py (Build-Logik), damit beide Dateien fokussiert bleiben.
Scan-Dirs sind projekt-relativ (zum Workspace) und werden gegen Path-Traversal
validiert — nur Verzeichnisse INNERHALB des Workspace sind erlaubt.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.projects._paths import workspace_path

# Verzeichnisse, die nie als Scan-Ziel taugen (Abhängigkeiten, Build-Artefakte).
IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".graphify", "generated",
    "mounts", "media", "venv", ".venv", "__pycache__", ".cache", "coverage",
}
# Verzeichnisnamen, die typischerweise Quellcode enthalten (Default-Vorschläge).
SOURCE_HINTS = {"src", "core", "server", "backend", "app", "lib"}


def _graphify_dir(project_id: str) -> Path:
    return workspace_path(project_id) / ".graphify"


def _config_path(project_id: str) -> Path:
    return _graphify_dir(project_id) / "config.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def suggest_scan_dirs(project_id: str) -> list[str]:
    """Schlägt Quellcode-Verzeichnisse vor: <repo>/src, <repo>/frontend/src etc.
    Sucht bis Tiefe 3 nach Ordnern mit typischem Source-Namen."""
    root = workspace_path(project_id)
    if not root.is_dir():
        return []
    found: list[str] = []

    def walk(d: Path, depth: int) -> None:
        if depth > 3:
            return
        for child in sorted(d.iterdir()):
            if not child.is_dir() or child.name in IGNORE_DIRS or child.name.startswith("."):
                continue
            rel = child.relative_to(root).as_posix()
            if child.name in SOURCE_HINTS:
                found.append(rel)
            else:
                walk(child, depth + 1)

    try:
        walk(root, 0)
    except OSError:
        pass
    return found[:20]


def _has_scannable_child(d: Path) -> bool:
    """Ob ein Ordner mindestens einen nicht-ignorierten Unterordner hat
    (für das Aufklapp-Chevron im Verzeichnis-Browser)."""
    try:
        for child in d.iterdir():
            if child.is_dir() and child.name not in IGNORE_DIRS and not child.name.startswith("."):
                return True
    except OSError:
        pass
    return False


def browse_dirs(project_id: str, rel_path: str = "") -> dict:
    """Direkte Unterverzeichnisse EINER Ebene für den Verzeichnis-Browser.

    Erlaubt granulare Auswahl beliebiger Ordner (z.B. `sdk/` tief im Baum),
    nicht nur die Namens-Heuristik aus suggest_scan_dirs. Traversal-geschützt:
    nur Verzeichnisse innerhalb des Workspace werden aufgelistet.
    Returns: {path, parent, dirs:[{rel, name, has_children}]}.
    """
    root = workspace_path(project_id).resolve()
    if not root.is_dir():
        return {"path": "", "parent": None, "dirs": []}
    target = (root / rel_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        target = root  # Traversal-Versuch → auf Workspace-Wurzel zurückfallen
    if not target.is_dir():
        target = root

    dirs: list[dict] = []
    try:
        for child in sorted(target.iterdir(), key=lambda c: c.name.lower()):
            if not child.is_dir() or child.name in IGNORE_DIRS or child.name.startswith("."):
                continue
            dirs.append({
                "rel": child.relative_to(root).as_posix(),
                "name": child.name,
                "has_children": _has_scannable_child(child),
            })
    except OSError:
        pass

    cur_rel = target.relative_to(root).as_posix() if target != root else ""
    parent = None if target == root else (
        target.parent.relative_to(root).as_posix() if target.parent != root else ""
    )
    return {"path": cur_rel, "parent": parent, "dirs": dirs}


def validate_scan_dirs(project_id: str, scan_dirs: list[str]) -> list[str]:
    """Filtert scan_dirs auf existierende Verzeichnisse INNERHALB des Workspace.
    Path-Traversal (../, absolute Pfade außerhalb) wird verworfen."""
    root = workspace_path(project_id).resolve()
    valid: list[str] = []
    for raw in scan_dirs:
        candidate = (root / raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue  # außerhalb des Workspace
        if candidate.is_dir() and candidate != root:
            rel = candidate.relative_to(root).as_posix()
            if rel not in valid:
                valid.append(rel)
    return valid


def get_config(project_id: str) -> dict:
    path = _config_path(project_id)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "scan_dirs": data.get("scan_dirs", []),
                    "updated_at": data.get("updated_at"),
                    "suggestions": suggest_scan_dirs(project_id),
                }
        except (OSError, json.JSONDecodeError):
            pass
    return {"scan_dirs": [], "updated_at": None, "suggestions": suggest_scan_dirs(project_id)}


def set_config(project_id: str, scan_dirs: list[str]) -> dict:
    valid = validate_scan_dirs(project_id, scan_dirs)
    path = _config_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"scan_dirs": valid, "updated_at": _now()}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)
    return {**payload, "suggestions": suggest_scan_dirs(project_id)}
