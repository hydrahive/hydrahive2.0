"""Markdown-File-I/O mit YAML-Frontmatter für WikiPages."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.wiki.models import WikiPage, make_slug
from hydrahive.settings import settings

_FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


def _wiki_dir() -> Path:
    d = settings.data_dir / "wiki"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(v) for v in val]
    if isinstance(val, str) and val.strip():
        return [v.strip() for v in val.split(",") if v.strip()]
    return []


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = _FM_RE.match(raw)
    if not m:
        return {}, raw
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    body = raw[m.end():]
    return fm, body


def _render(page: WikiPage) -> str:
    tags = ", ".join(page.tags)
    entities = ", ".join(page.entities)
    return (
        f"---\n"
        f"title: {page.title}\n"
        f"slug: {page.slug}\n"
        f"tags: {tags}\n"
        f"entities: {entities}\n"
        f"source_url: {page.source_url}\n"
        f"author: {page.author}\n"
        f"created_at: {page.created_at}\n"
        f"updated_at: {page.updated_at}\n"
        f"---\n"
        f"{page.body}"
    )


def _path(slug: str) -> Path:
    return _wiki_dir() / f"{slug}.md"


def load(slug: str) -> WikiPage | None:
    p = _path(slug)
    if not p.exists():
        return None
    fm, body = _parse_frontmatter(p.read_text(encoding="utf-8"))
    return WikiPage(
        slug=slug,
        title=fm.get("title", slug),
        body=body,
        tags=_parse_list(fm.get("tags", "")),
        entities=_parse_list(fm.get("entities", "")),
        source_url=fm.get("source_url", ""),
        author=fm.get("author", ""),
        created_at=fm.get("created_at", ""),
        updated_at=fm.get("updated_at", ""),
    )


def save(page: WikiPage) -> WikiPage:
    now = _now()
    if not page.created_at:
        page.created_at = now
    page.updated_at = now
    p = _path(page.slug)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(_render(page), encoding="utf-8")
    os.replace(tmp, p)
    return page


def delete(slug: str) -> bool:
    p = _path(slug)
    if not p.exists():
        return False
    p.unlink()
    return True


def list_all() -> list[WikiPage]:
    pages = []
    for f in sorted(_wiki_dir().glob("*.md")):
        page = load(f.stem)
        if page:
            pages.append(page)
    return pages


def slug_exists(slug: str) -> bool:
    return _path(slug).exists()
