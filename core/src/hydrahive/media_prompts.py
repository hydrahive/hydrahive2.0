from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hydrahive import media_projects

_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
TYPES = frozenset({"general", "image", "video", "music", "voice", "storyboard"})
STATUSES = frozenset({"draft", "executed", "archived"})


class MediaPromptError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _paths(project_id: str, media_slug: str, prompt_type: str, slug: str | None = None) -> tuple[Path, Path | None]:
    project_path = media_projects._dir(project_id, media_slug)
    if not (project_path / "media-project.json").is_file():
        raise FileNotFoundError(media_slug)
    if prompt_type not in TYPES:
        raise MediaPromptError("Ungültiger Prompt-Typ")
    root = (project_path / "prompts" / prompt_type).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if slug is None:
        return root, None
    if not _SLUG.fullmatch(slug):
        raise MediaPromptError("Ungültiger Prompt-Slug")
    path = (root / f"{slug}.md").resolve()
    if path.parent != root:
        raise MediaPromptError("Ungültiger Prompt-Pfad")
    return root, path


def _read(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise MediaPromptError("Prompt-Metadaten fehlen")
        frontmatter, separator, body = text[4:].partition("\n---\n")
        if not separator:
            raise MediaPromptError("Prompt-Metadaten sind ungültig")
        data = yaml.safe_load(frontmatter)
        if not isinstance(data, dict):
            raise MediaPromptError("Prompt-Metadaten sind ungültig")
        data["body"] = body.lstrip("\n")
        return data
    except (OSError, yaml.YAMLError) as exc:
        raise MediaPromptError("Prompt konnte nicht gelesen werden") from exc


def _write(path: Path, data: dict) -> None:
    metadata = {key: value for key, value in data.items() if key != "body"}
    content = f"---\n{yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)}---\n\n{data.get('body', '').rstrip()}\n"
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def list_all(project_id: str, media_slug: str, prompt_type: str | None = None) -> list[dict]:
    types = [prompt_type] if prompt_type is not None else sorted(TYPES)
    result: list[dict] = []
    for kind in types:
        root, _ = _paths(project_id, media_slug, kind)
        for path in sorted(root.glob("*.md")):
            try:
                result.append(_read(path))
            except MediaPromptError:
                continue
    return sorted(result, key=lambda item: item.get("updated_at", ""), reverse=True)


def get(project_id: str, media_slug: str, prompt_type: str, slug: str) -> dict | None:
    _, path = _paths(project_id, media_slug, prompt_type, slug)
    return _read(path) if path and path.is_file() else None


def create(project_id: str, media_slug: str, prompt_type: str, slug: str, title: str, body: str, *, model: str = "", asset_refs: list[str] | None = None) -> dict:
    _, path = _paths(project_id, media_slug, prompt_type, slug)
    assert path is not None
    if path.exists():
        raise FileExistsError(slug)
    now = _now()
    data = {"version": 1, "slug": slug, "type": prompt_type, "title": title.strip(), "status": "draft", "model": model.strip(), "asset_refs": asset_refs or [], "result_refs": [], "created_at": now, "updated_at": now, "body": body}
    _write(path, data)
    return data


def update(project_id: str, media_slug: str, prompt_type: str, slug: str, **changes: object) -> dict:
    _, path = _paths(project_id, media_slug, prompt_type, slug)
    assert path is not None
    if not path.is_file():
        raise FileNotFoundError(slug)
    data = _read(path)
    if "status" in changes and changes["status"] not in STATUSES:
        raise MediaPromptError("Ungültiger Prompt-Status")
    for key in ("title", "body", "model", "status", "asset_refs", "result_refs"):
        if key in changes and changes[key] is not None:
            data[key] = changes[key]
    data["updated_at"] = _now()
    _write(path, data)
    return data


def delete(project_id: str, media_slug: str, prompt_type: str, slug: str) -> bool:
    _, path = _paths(project_id, media_slug, prompt_type, slug)
    assert path is not None
    if not path.is_file():
        return False
    path.unlink()
    return True
