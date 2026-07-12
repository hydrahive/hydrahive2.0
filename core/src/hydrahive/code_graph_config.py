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
