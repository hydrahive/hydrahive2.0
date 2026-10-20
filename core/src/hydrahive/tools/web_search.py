from __future__ import annotations

import httpx

from hydrahive.settings.overrides import resolve as resolve_setting
from hydrahive.tools import _search_params as sp
from hydrahive.tools import _tavily
from hydrahive.tools._searx_outage import describe, unavailable_engines
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Websuche über lokalen SearxNG. Gibt Titel, URL, Snippet, Quelle und – falls bekannt – "
    "das Datum (published) zurück. Für aktuelle Ereignisse category='news' und time_range "
    "(day/week/month/year) nutzen. Fallen die Suchanbieter aus und ist ein Tavily-Schlüssel "
    "eingetragen, springt Tavily automatisch ein (provider='tavily'); bei wenigen allgemeinen "
    "Treffern ergänzt Tavily die Liste (supplemented='tavily')."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Suchanfrage."},
        "count": {"type": "integer", "description": "Anzahl Ergebnisse (default 10).", "default": 10},
        "category": {"type": "string", "enum": list(sp.CATEGORIES), "default": "general",
                     "description": "general = Web, news = Nachrichten (für Aktuelles)."},
        "time_range": {"type": "string", "enum": list(sp.TIME_RANGES),
                       "description": "Optional: nur Treffer aus diesem Zeitraum."},
    },
    "required": ["query"],
}


class _SearxFailed(Exception):
    pass


async def _ask_searx(base: str, params: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{base}/search", params=params)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise _SearxFailed(f"SearxNG-Request fehlgeschlagen: {e}") from None
    except ValueError:
        raise _SearxFailed("SearxNG-Antwort kein JSON") from None


async def _tavily_fallback(query: str, category: str, time_range: str | None, count: int,
                           searx_problem: str, unavailable: list) -> ToolResult | None:
    """None = kein Schlüssel eingetragen → Verhalten wie ohne Tavily."""
    api_key = (resolve_setting("tavily_api_key") or "").strip()
    if not api_key:
        return None
    if not _tavily.reserve():
        return ToolResult.fail(f"{searx_problem} Tavily-Monatskontingent fast aufgebraucht "
                               f"({_tavily.MONTHLY_STOP} Aufrufe) – Ersatz pausiert bis Monatsende.")
    try:
        data = await _tavily.search(query, topic=category, time_range=time_range,
                                    count=count, api_key=api_key)
    except _tavily.TavilyError as e:
        return ToolResult.fail(f"{searx_problem} Ersatz fehlgeschlagen: {e}")
    output: dict = {"query": query, "results": data["results"][:count],
                    "count": len(data["results"][:count]), "provider": "tavily"}
    if unavailable:
        output["unavailable"] = unavailable
    return ToolResult.ok(output)


SUPPLEMENT_BELOW = 3      # Spec websuche-kostenlos §11.1: weniger allgemeine Treffer → Tavily ergänzt


async def _supplement(output: dict, query: str, time_range: str | None, count: int) -> None:
    """Variante C: wenige allgemeine Treffer um Tavily ergänzen (ohne Doppel). Fehler/Kontingent → nur Hinweis."""
    api_key = (resolve_setting("tavily_api_key") or "").strip()
    if not api_key:
        return
    if not _tavily.reserve():
        output["supplement_note"] = f"Tavily-Monatskontingent fast aufgebraucht ({_tavily.MONTHLY_STOP}) – nicht ergänzt."
        return
    try:
        data = await _tavily.search(query, topic="general", time_range=time_range, count=count, api_key=api_key)
    except _tavily.TavilyError as e:
        output["supplement_note"] = f"Ergänzung fehlgeschlagen: {e}"
        return
    seen = {h["url"] for h in output["results"]}
    extra = [h for h in data["results"] if h.get("url") and h["url"] not in seen]
    if extra:
        output["results"] = (output["results"] + extra)[:count]
        output["count"] = len(output["results"])
        output["supplemented"] = "tavily"


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    query = args.get("query", "").strip()
    if not query:
        return ToolResult.fail("Leere Suchanfrage")
    category, time_range, problem = sp.validate(args)
    if problem:
        return ToolResult.fail(problem)

    # Tool-Config (pro Agent) hat Vorrang; sonst die globale Einstellung
    # (GUI-Override → HH_SEARXNG_URL).
    base = (ctx.config.get("searxng_url") or resolve_setting("searxng_url") or "").rstrip("/")
    if not base:
        return ToolResult.fail("SearxNG nicht konfiguriert — URL in den Einstellungen hinterlegen")

    count = max(1, min(50, int(args.get("count", 10))))

    try:
        data = await _ask_searx(base, sp.searx_params(query, category, time_range))
        fallback = None
        if not data.get("results") and category == "general" and time_range:
            # Allgemeine Anbieter liefern mit Zeitraum oft nichts – News schon (Messung 20.10.).
            data = await _ask_searx(base, sp.searx_params(query, "news", time_range))
            fallback = "news"
    except _SearxFailed as e:
        return await _tavily_fallback(query, category, time_range, count, f"{e}.", []) \
            or ToolResult.fail(str(e))

    results = [sp.map_hit(item) for item in (data.get("results") or [])[:count]]
    unavailable = unavailable_engines(data)
    if not results and unavailable:
        # Alle befragten Anbieter gesperrt — nicht als „gibt nichts“ tarnen.
        blocked = ("Websuche liefert keine Treffer — Suchanbieter gesperrt: "
                   f"{describe(unavailable)}.")
        return await _tavily_fallback(query, category, time_range, count, blocked, unavailable) \
            or ToolResult.fail(f"{blocked} Dienst prüfen (SearXNG).")
    output: dict = {"query": query, "results": results, "count": len(results)}
    if fallback:
        output["fallback"] = fallback
    if category == "general" and not fallback and len(results) < SUPPLEMENT_BELOW:
        await _supplement(output, query, time_range, count)
    if unavailable:
        output["unavailable"] = unavailable
    return ToolResult.ok(output)


TOOL = Tool(name="web_search", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="web")
