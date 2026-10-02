from __future__ import annotations

import httpx

from hydrahive.settings.overrides import resolve as resolve_setting
from hydrahive.tools._searx_outage import describe, unavailable_engines
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Websuche über lokalen SearxNG. Gibt Titel, URL, Snippet zurück. "
    "URL kommt aus den Einstellungen (SearXNG-URL) bzw. HH_SEARXNG_URL."
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

    # Tool-Config (pro Agent) hat Vorrang; sonst die globale Einstellung
    # (GUI-Override → HH_SEARXNG_URL).
    base = (ctx.config.get("searxng_url") or resolve_setting("searxng_url") or "").rstrip("/")
    if not base:
        return ToolResult.fail("SearxNG nicht konfiguriert — URL in den Einstellungen hinterlegen")

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
    unavailable = unavailable_engines(data)
    if not results and unavailable:
        # Alle befragten Anbieter gesperrt — nicht als „gibt nichts“ tarnen.
        return ToolResult.fail(
            "Websuche liefert keine Treffer — Suchanbieter gesperrt: "
            f"{describe(unavailable)}. Dienst prüfen (SearXNG)."
        )
    output: dict = {"query": query, "results": results, "count": len(results)}
    if unavailable:
        output["unavailable"] = unavailable
    return ToolResult.ok(output)


TOOL = Tool(name="web_search", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="web")
