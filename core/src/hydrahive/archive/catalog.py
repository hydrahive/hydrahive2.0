"""Katalog des System-Archivs: liest die .json neben den Paketen.

Keine Datenbank: Die Freigabe ist beschreibbar (Samba), Dateien kommen und
gehen auch ohne HydraHive. Was keine .json hat, gilt als „von Hand abgelegt“
(manual). Papierkorb und halbfertige Pakete (.part) werden nie gelistet.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from hydrahive.archive._paths import KINDS, TRASH_DIR, archive_root

logger = logging.getLogger(__name__)


def _is_hidden(rel: Path) -> bool:
    return rel.parts[0] == TRASH_DIR or rel.name.endswith(".part") or rel.name.startswith(".")


def _walk_files(root: Path):
    for dirpath, dirs, files in os.walk(root, followlinks=False):
        here = Path(dirpath)
        dirs[:] = [d for d in dirs if not (here == root and d == TRASH_DIR) and not d.startswith(".")]
        for f in files:
            yield here / f


def _manual(path: Path, root: Path) -> dict:
    st = path.lstat()
    rel = path.relative_to(root)
    kind = rel.parts[0] if len(rel.parts) > 1 and rel.parts[0] in KINDS else None
    from hydrahive.archive._remote_files import remote_of
    return {"manual": True, "path": str(rel), "file": path.name, "kind": kind,
            "size": st.st_size, "mtime": st.st_mtime, "remote": remote_of(str(rel).replace(os.sep, "/"))}


def _packaged(path: Path, root: Path) -> dict | None:
    meta_path = path.with_name(path.name + ".json")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict):
        return None
    return {**meta, "manual": False, "path": str(path.relative_to(root)),
            "mtime": meta_path.stat().st_mtime}


def list_entries(kind: str | None = None) -> list[dict]:
    """Alle Archiv-Einträge, neueste zuerst. `kind` filtert nach Unterordner."""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"Unbekannte Archiv-Art: {kind!r}")
    root = archive_root()
    if not root.is_dir():
        return []
    out: list[dict] = []
    for path in _walk_files(root):
        rel = path.relative_to(root)
        if _is_hidden(rel) or path.name.endswith(".tar.gz.json"):
            continue
        entry = _packaged(path, root) if path.name.endswith(".tar.gz") else None
        if entry is None:
            entry = _manual(path, root)
        if kind is None or rel.parts[0] == kind:
            out.append(entry)
    out.sort(key=lambda e: e["mtime"], reverse=True)
    return out


def _tree_bytes(path: Path) -> int:
    total = 0
    for f in _walk_all(path):
        try:
            total += f.lstat().st_size
        except OSError:
            pass
    return total


def _walk_all(path: Path):
    for dirpath, _dirs, files in os.walk(path, followlinks=False):
        for f in files:
            yield Path(dirpath) / f


def usage() -> dict:
    """Platz und Zählung für das Admin-Fenster."""
    root = archive_root()
    exists = root.is_dir()
    entries = list_entries() if exists else []
    by_kind: dict[str, int] = {}
    for e in entries:
        if not e["manual"]:
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    probe = root if exists else root.parent
    free = shutil.disk_usage(probe).free if probe.exists() else 0
    return {
        "path": str(root), "exists": exists,
        "writable": exists and os.access(root, os.W_OK | os.X_OK),
        "count": sum(by_kind.values()), "manual_count": sum(1 for e in entries if e["manual"]),
        "by_kind": by_kind, "used_bytes": sum(e.get("size", 0) for e in entries),
        "free_bytes": free, "trash_bytes": _tree_bytes(root / TRASH_DIR) if exists else 0,
    }
