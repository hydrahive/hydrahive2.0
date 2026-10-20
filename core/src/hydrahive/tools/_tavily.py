"""Tavily als Ersatz-Suche, wenn SearXNG ausfällt (Spec docs/specs/websuche-kostenlos.md §5).

Kostenlos: 1.000 Credits pro Monat ohne Kreditkarte, eine Basic-Suche kostet 1 Credit
(docs.tavily.com, abgerufen 20.10.2026). Der eigene Zähler hört bei 950 auf, damit das
Gratis-Kontingent auch bei Fehlversuchen nie überschritten wird.

Der Schlüssel geht nur als Header raus. Fehlermeldungen enthalten nie den Schlüssel oder
den Antwortkörper.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

import httpx

from hydrahive.settings import settings

URL = "https://api.tavily.com/search"
MONTHLY_STOP = 950
MAX_RESULTS = 20
_TIMEOUT = 20.0
_LOCK = threading.Lock()


class TavilyError(Exception):
    """Kurze, schlüsselfreie Fehlermeldung für den Agenten."""


def _usage_path() -> Path:
    return settings.data_dir / "websearch" / "tavily_usage.json"


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_count(path: Path, month: str) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict) or data.get("month") != month:
        return 0
    count = data.get("count")
    return count if isinstance(count, int) and count >= 0 else 0


def reserve() -> bool:
    """Zählt einen Aufruf VOR dem Request. False = Monatsgrenze erreicht, nicht aufrufen."""
    month = _month()
    path = _usage_path()
    with _LOCK:
        count = _load_count(path, month)
        if count >= MONTHLY_STOP:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"month": month, "count": count + 1}), encoding="utf-8")
        os.replace(tmp, path)
        return True


def _map(item: dict) -> dict:
    hit = {
        "title": str(item.get("title") or ""),
        "url": str(item.get("url") or ""),
        "snippet": str(item.get("content") or ""),
        "source": "tavily",
    }
    if item.get("published_date"):
        hit["published"] = str(item["published_date"])
    return hit


async def search(query: str, *, topic: str, time_range: str | None, count: int, api_key: str) -> dict:
    body: dict = {
        "query": query,
        "search_depth": "basic",
        "topic": topic,
        "max_results": max(1, min(MAX_RESULTS, count)),
    }
    if time_range:
        body["time_range"] = time_range
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(URL, json=body, headers={"Authorization": f"Bearer {api_key}"})
    except httpx.HTTPError as e:
        raise TavilyError(f"Tavily nicht erreichbar ({type(e).__name__})") from None
    if r.status_code != 200:
        raise TavilyError(f"Tavily: HTTP {r.status_code}")
    try:
        data = r.json()
    except ValueError:
        raise TavilyError("Tavily-Antwort kein JSON") from None
    items = data.get("results") if isinstance(data, dict) else None
    return {"results": [_map(i) for i in (items or []) if isinstance(i, dict)]}
