from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.projects._paths import ensure_workspace

_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_DIRS = ("prompts", "assets", "images", "video", "audio", "timeline", "exports")


class MediaProjectError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(project_id: str) -> Path:
    return ensure_workspace(project_id) / "media"


def _dir(project_id: str, slug: str) -> Path:
    if not _SLUG.fullmatch(slug):
        raise MediaProjectError("Ungültiger Media-Projekt-Slug")
    root = _root(project_id).resolve()
    target = (root / slug).resolve()
    if target.parent != root:
        raise MediaProjectError("Ungültiger Media-Projekt-Pfad")
    return target


def _read(path: Path) -> dict:
    try:
        return json.loads((path / "media-project.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MediaProjectError("Media-Projekt konnte nicht gelesen werden") from exc


def _write(path: Path, data: dict) -> None:
    tmp = path / ".media-project.json.tmp"
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path / "media-project.json")
    (path / "project.md").write_text(
        f"# {data['name']}\n\n{data.get('description') or 'Keine Beschreibung.'}\n\n"
        f"- Heimatprojekt: `{data['project_id']}`\n- Media-Slug: `{data['slug']}`\n",
        encoding="utf-8",
    )


def list_all(project_id: str) -> list[dict]:
    root = _root(project_id)
    if not root.exists():
        return []
    result = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and _SLUG.fullmatch(child.name) and (child / "media-project.json").is_file():
            try:
                result.append(_read(child))
            except MediaProjectError:
                continue
    return result


def get(project_id: str, slug: str) -> dict | None:
    path = _dir(project_id, slug)
    return _read(path) if (path / "media-project.json").is_file() else None


def create(project_id: str, slug: str, name: str, description: str = "") -> dict:
    path = _dir(project_id, slug)
    if path.exists():
        raise FileExistsError(slug)
    path.mkdir(parents=True)
    for dirname in _DIRS:
        (path / dirname).mkdir()
    now = _now()
    data = {"version": 1, "slug": slug, "name": name.strip(), "description": description.strip(), "project_id": project_id, "created_at": now, "updated_at": now}
    _write(path, data)
    return data


def update(project_id: str, slug: str, *, name: str | None = None, description: str | None = None) -> dict:
    path = _dir(project_id, slug)
    if not (path / "media-project.json").is_file():
        raise FileNotFoundError(slug)
    data = _read(path)
    if name is not None:
        data["name"] = name.strip()
    if description is not None:
        data["description"] = description.strip()
    data["updated_at"] = _now()
    _write(path, data)
    return data


def delete(project_id: str, slug: str) -> bool:
    path = _dir(project_id, slug)
    if not path.exists():
        return False
    shutil.rmtree(path)
    return True
