from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from hydrahive import media_projects
from hydrahive.projects._paths import workspace_path

_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
KINDS = frozenset({"character", "style", "image", "video", "audio", "voice", "other"})


class MediaAssetError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(project_id: str, media_slug: str) -> Path:
    root = media_projects._dir(project_id, media_slug)
    if not (root / "media-project.json").is_file():
        raise FileNotFoundError(media_slug)
    return root


def _index(project_id: str, media_slug: str) -> Path:
    return _root(project_id, media_slug) / "assets" / "references.json"


def _load(project_id: str, media_slug: str) -> list[dict]:
    path = _index(project_id, media_slug)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        raise MediaAssetError("Asset-Referenzen konnten nicht gelesen werden") from exc


def _write(project_id: str, media_slug: str, items: list[dict]) -> None:
    path = _index(project_id, media_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _source(source_project_id: str, rel_path: str) -> Path:
    root = workspace_path(source_project_id).resolve()
    try:
        target = (root / rel_path).resolve()
        target.relative_to(root)
    except (OSError, ValueError) as exc:
        raise MediaAssetError("Ungültiger Asset-Pfad") from exc
    if not target.is_file():
        raise FileNotFoundError(rel_path)
    return target


def list_all(project_id: str, media_slug: str) -> list[dict]:
    result = []
    for item in _load(project_id, media_slug):
        current = dict(item)
        try:
            _source(current["source_project_id"], current["rel_path"])
            current["available"] = True
        except (FileNotFoundError, MediaAssetError):
            current["available"] = False
        result.append(current)
    return result


def create(project_id: str, media_slug: str, asset_id: str, kind: str, source_project_id: str, rel_path: str, label: str) -> dict:
    if not _ID.fullmatch(asset_id) or kind not in KINDS:
        raise MediaAssetError("Ungültige Asset-Referenz")
    _source(source_project_id, rel_path)
    items = _load(project_id, media_slug)
    if any(item["id"] == asset_id for item in items):
        raise FileExistsError(asset_id)
    now = _now()
    item = {"version": 1, "id": asset_id, "kind": kind, "label": label.strip(), "source_project_id": source_project_id, "rel_path": rel_path, "mode": "reference", "read_only": True, "created_at": now, "updated_at": now}
    items.append(item)
    _write(project_id, media_slug, items)
    return {**item, "available": True}


def delete(project_id: str, media_slug: str, asset_id: str) -> bool:
    if not _ID.fullmatch(asset_id):
        raise MediaAssetError("Ungültige Asset-ID")
    items = _load(project_id, media_slug)
    filtered = [item for item in items if item["id"] != asset_id]
    if len(filtered) == len(items):
        return False
    _write(project_id, media_slug, filtered)
    return True


def import_copy(project_id: str, media_slug: str, asset_id: str) -> dict:
    items = _load(project_id, media_slug)
    item = next((entry for entry in items if entry["id"] == asset_id), None)
    if item is None:
        raise FileNotFoundError(asset_id)
    source = _source(item["source_project_id"], item["rel_path"])
    destination_dir = _root(project_id, media_slug) / "assets" / "imported"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{asset_id}{source.suffix.lower()}"
    shutil.copy2(source, destination)
    item.update({"source_project_id": project_id, "rel_path": str(destination.relative_to(workspace_path(project_id))), "mode": "copy", "read_only": False, "updated_at": _now()})
    _write(project_id, media_slug, items)
    return {**item, "available": True}
