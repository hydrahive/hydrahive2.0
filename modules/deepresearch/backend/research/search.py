"""SearxNG-Suche — gleiche Quelle wie das Core-Tool web_search.py."""
from __future__ import annotations

import logging

import httpx

from hydrahive.settings.overrides import resolve as resolve_setting

logger = logging.getLogger(__name__)


async def searxng_search(query: str, count: int = 8) -> list[dict]:
    """Gibt [{title, url, snippet}] zurück. Bei Fehler/Nichtkonfiguration: leere Liste."""
    base = (resolve_setting("searxng_url") or "").rstrip("/")
    if not base:
        logger.warning("deepresearch: SearxNG nicht konfiguriert (searxng_url)")
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{base}/search",
                params={"q": query, "format": "json", "language": "de"},
            )
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("deepresearch: SearxNG-Suche fehlgeschlagen (%s): %s", query, e)
        return []

    out: list[dict] = []
    for item in (data.get("results") or [])[:count]:
        url = item.get("url", "")
        if url:
            out.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("content", ""),
            })
    return out
