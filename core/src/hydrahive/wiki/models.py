"""WikiPage-Modell — Plain-Text Markdown mit YAML-Frontmatter."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")


@dataclass
class WikiPage:
    slug: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    source_url: str = ""
    author: str = ""
    created_at: str = ""
    updated_at: str = ""

    def outgoing_links(self) -> list[str]:
        """Slugs aller [[WikiLinks]] im Body."""
        return [_to_slug(m) for m in WIKILINK_RE.findall(self.body)]


def _to_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def make_slug(title: str) -> str:
    return _to_slug(title)
