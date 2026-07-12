"""Verwaltung der fertigen Film-Exporte (Historie): Auflisten & Löschen.

Der eigentliche Render liegt in media_export.py; hier die persistente Sicht auf
die erzeugten MP4s (+ Sidecar-Meta) im exports/-Ordner eines Media-Projekts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from hydrahive import media_projects


class MediaExportError(ValueError):
    pass


def list_exports(project_id: str, media_slug: str) -> list[dict]:
    """Alle fertigen Export-MP4s eines Media-Projekts, neueste zuerst."""
    root = media_projects._dir(project_id, media_slug)
    exports_dir = root / "exports"
    if not exports_dir.is_dir():
        return []
    items: list[dict] = []
    for mp4 in exports_dir.glob("*.mp4"):
        meta: dict = {}
        sidecar = mp4.with_suffix(".json")
        if sidecar.is_file():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
        stat = mp4.stat()
        items.append({
            "name": mp4.name,
            "rel_path": str(mp4.relative_to(root)),
            "path": str(mp4),
            "size": stat.st_size,
            "created_at": meta.get("created_at") or datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "duration": meta.get("duration"),
        })
    items.sort(key=lambda e: e["created_at"], reverse=True)
    return items


def delete_export(project_id: str, media_slug: str, name: str) -> None:
    """Löscht eine Export-Datei + Sidecar. name ist ein Basename im exports/-Ordner."""
    root = media_projects._dir(project_id, media_slug)
    exports_dir = (root / "exports").resolve()
    target = (exports_dir / name).resolve()
    if target.parent != exports_dir or target.suffix != ".mp4":
        raise MediaExportError("Ungültiger Export-Name")
    if not target.is_file():
        raise FileNotFoundError(name)
    target.unlink()
    sidecar = target.with_suffix(".json")
    if sidecar.is_file():
        sidecar.unlink()
