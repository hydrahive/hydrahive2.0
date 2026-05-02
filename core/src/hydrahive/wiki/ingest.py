"""URL/Text-Ingestion für HydraWiki.

Flow:
1. URL → httpx fetch → HTML-Text extrahieren
   Text → direkt übernehmen
2. LLM-Call: {title, summary, entities, tags, links_to}
3. WikiPage speichern + Index aktualisieren
"""
from __future__ import annotations

import json
import logging
import re

import httpx

from hydrahive.llm import client as llm_client
from hydrahive.wiki import index as wiki_index
from hydrahive.wiki import storage as wiki_storage
from hydrahive.wiki.models import WikiPage, make_slug

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\n{3,}")
_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)


def _strip_html(html: str) -> str:
    text = _SCRIPT_RE.sub("", html)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = _SPACE_RE.sub("\n\n", text)
    return text.strip()


async def _fetch_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True,
                                  headers={"User-Agent": "HydraWiki/1.0"}) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "html" in ct:
            return _strip_html(resp.text)
        return resp.text


_EXTRACT_PROMPT = """\
Analysiere den folgenden Text und antworte NUR mit einem JSON-Objekt, kein Markdown, kein Text davor oder danach.

JSON-Schema:
{{
  "title": "Kurzer präziser Titel (max 80 Zeichen)",
  "summary": "Ausführliche Zusammenfassung mit allen wichtigen Informationen, Konzepten, Befehlen und Details aus dem Text. Nutze Markdown: Absätze, ## Überschriften, - Listen, `Code`. Mindestens 500 Wörter wenn der Inhalt es hergibt.",
  "tags": ["tag1", "tag2", "tag3"],
  "entities": ["Entität1", "Entität2"],
  "links_to": ["bestehende-wiki-seite-slug"]
}}

Bekannte Wiki-Seiten (nur diese als links_to verwenden falls relevant):
{known_slugs}

Text:
{text}
"""


async def _extract(text: str, known_slugs: list[str]) -> dict:
    prompt = _EXTRACT_PROMPT.format(
        known_slugs=", ".join(known_slugs) if known_slugs else "(keine)",
        text=text[:12000],
    )
    raw = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0.2,
    )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


async def ingest(
    url: str | None = None,
    text: str | None = None,
    title_hint: str | None = None,
    author: str = "system",
) -> WikiPage:
    if not url and not text:
        raise ValueError("url oder text erforderlich")

    source_url = url or ""
    if url:
        raw_text = await _fetch_url(url)
    else:
        raw_text = text or ""

    known = [p.slug for p in wiki_storage.list_all()]

    try:
        extracted = await _extract(raw_text, known)
    except Exception as e:
        logger.warning("LLM-Extraktion fehlgeschlagen: %s — Fallback auf Basis-Daten", e)
        extracted = {"title": title_hint or (url or "Neue Seite"), "summary": raw_text[:500],
                     "tags": [], "entities": [], "links_to": []}

    title = title_hint or extracted.get("title") or (url or "Neue Seite")
    slug = make_slug(title)

    # Slug-Konflikt auflösen
    base_slug = slug
    i = 2
    while wiki_storage.slug_exists(slug):
        slug = f"{base_slug}-{i}"
        i += 1

    # links_to → [[WikiLink]] im Body
    links_to: list[str] = extracted.get("links_to", [])
    body = extracted.get("summary", raw_text[:2000])
    if links_to:
        body += "\n\n**Verwandte Seiten:** " + " ".join(f"[[{s}]]" for s in links_to)

    page = WikiPage(
        slug=slug, title=title, body=body,
        tags=extracted.get("tags", []),
        entities=extracted.get("entities", []),
        source_url=source_url, author=author,
    )
    page = wiki_storage.save(page)
    wiki_index.upsert(page)
    return page
