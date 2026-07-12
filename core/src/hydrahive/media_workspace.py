from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from hydrahive import media_projects


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(project_id: str, media_slug: str) -> Path:
    root = media_projects._dir(project_id, media_slug)
    if not (root / "media-project.json").is_file():
        raise FileNotFoundError(media_slug)
    return root


def _atomic(path: Path, data: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return data


def _read(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else default
    except (OSError, json.JSONDecodeError):
        return default


def screenplay(project_id: str, media_slug: str) -> dict:
    default = {"version": 1, "title": "", "logline": "", "acts": [], "updated_at": None}
    return _read(_root(project_id, media_slug) / "screenplay.json", default)


def save_screenplay(project_id: str, media_slug: str, data: dict) -> dict:
    value = {"version": 1, "title": data.get("title", ""), "logline": data.get("logline", ""), "acts": data.get("acts", []), "updated_at": _now()}
    return _atomic(_root(project_id, media_slug) / "screenplay.json", value)


def agent_context(project_id: str, media_slug: str) -> dict:
    default = {"version": 1, "note": "", "active_scene_id": None, "asset_ids": [], "prompt_draft": "", "updated_at": None}
    return _read(_root(project_id, media_slug) / "agent" / "context.json", default)


def save_agent_context(project_id: str, media_slug: str, data: dict) -> dict:
    value = {"version": 1, "note": data.get("note", ""), "active_scene_id": data.get("active_scene_id"), "asset_ids": data.get("asset_ids", []), "prompt_draft": data.get("prompt_draft", ""), "updated_at": _now()}
    return _atomic(_root(project_id, media_slug) / "agent" / "context.json", value)


def timeline(project_id: str, media_slug: str) -> dict:
    default = {"version": 1, "fps": 25, "width": 1920, "height": 1080, "tracks": [], "cut_points": [], "updated_at": None}
    return _read(_root(project_id, media_slug) / "timeline" / "timeline.json", default)


def save_timeline(project_id: str, media_slug: str, data: dict) -> dict:
    value = {"version": 1, "fps": data.get("fps", 25), "width": data.get("width", 1920), "height": data.get("height", 1080), "tracks": data.get("tracks", []), "cut_points": data.get("cut_points", []), "updated_at": _now()}
    return _atomic(_root(project_id, media_slug) / "timeline" / "timeline.json", value)
