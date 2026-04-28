from __future__ import annotations

import httpx

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Websuche über lokalen SearxNG. Gibt Titel, URL, Snippet zurück. "
    "Braucht `searxng_url` in der Tool-Config."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Suchanfrage."},
        "count": {"type": "integer", "description": "Anzahl Ergebnisse (default 10).", "default": 10},
    },
    "required": ["query"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    query = args.get("query", "").strip()
    if not query:
        return ToolResult.fail("Leere Suchanfrage")

    base = (ctx.config.get("searxng_url") or "").rstrip("/")
    if not base:
        return ToolResult.fail("SearxNG nicht konfiguriert (searxng_url fehlt)")

    count = max(1, min(50, int(args.get("count", 10))))

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{base}/search",
                params={"q": query, "format": "json", "language": "de"},
            )
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPError as e:
        return ToolResult.fail(f"SearxNG-Request fehlgeschlagen: {e}")
    except ValueError:
        return ToolResult.fail("SearxNG-Antwort kein JSON")

    results = []
    for item in (data.get("results") or [])[:count]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
        })
    return ToolResult.ok({"query": query, "results": results, "count": len(results)})


TOOL = Tool(name="web_search", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
