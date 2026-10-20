"""Parameter und Treffer-Format von web_search (Spec docs/specs/websuche-kostenlos.md §4)."""
from __future__ import annotations

from urllib.parse import urlsplit

CATEGORIES = ("general", "news")
TIME_RANGES = ("day", "week", "month", "year")


def validate(args: dict) -> tuple[str, str | None, str | None]:
    """(category, time_range, fehler). Fehler = verständlicher Text, sonst None."""
    category = args.get("category", "general")
    if category not in CATEGORIES:
        return "", None, f"Unbekannte category – erlaubt: {', '.join(CATEGORIES)}"
    time_range = args.get("time_range")
    if time_range is not None and time_range not in TIME_RANGES:
        return "", None, f"Unbekannter time_range – erlaubt: {', '.join(TIME_RANGES)}"
    return category, time_range, None


def searx_params(query: str, category: str, time_range: str | None) -> dict:
    """Ohne neue Parameter genau die Anfrage von früher (q, format, language)."""
    params = {"q": query, "format": "json", "language": "de"}
    if category != "general":
        params["categories"] = category
    if time_range:
        params["time_range"] = time_range
    return params


def usable(item: object) -> bool:
    """Nur Treffer mit http(s)-URL samt Host. SearXNG lieferte am 20.10.2026 von Google
    „http:///url?opi=…“ – ohne Host, für den Agenten wertlos."""
    if not isinstance(item, dict) or not isinstance(item.get("url"), str):
        return False
    try:
        parts = urlsplit(item["url"].strip())
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname)


def map_hit(item: dict) -> dict:
    hit = {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "snippet": item.get("content", ""),
        "source": item.get("engine") or "",
    }
    published = item.get("publishedDate")
    if isinstance(published, str) and published.strip():
        hit["published"] = published.strip()[:10]
    return hit
