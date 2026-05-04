"""Datamining-Tools — Langzeitgedächtnis für HydraHive-Agenten."""
from __future__ import annotations

from datetime import datetime, timezone

from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _serialize(obj):
    """Konvertiert datetime-Objekte in ISO-Strings für JSON-Serialisierung."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj

_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query":      {"type": "string", "description": "Suchbegriff"},
        "event_type": {"type": "string", "description": "Optional: user_input|assistant_text|tool_call|tool_result"},
        "agent_name": {"type": "string", "description": "Optional: nur Events dieses Agents"},
        "from_date":  {"type": "string", "description": "Optional: ISO-Datum z.B. 2026-01-01"},
        "to_date":    {"type": "string", "description": "Optional: ISO-Datum"},
        "limit":      {"type": "integer", "default": 20, "description": "Max. Ergebnisse (1-50)"},
    },
    "required": ["query"],
}

_SEMANTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "query":      {"type": "string", "description": "Semantische Suchanfrage — findet inhaltlich Ähnliches"},
        "event_type": {"type": "string"},
        "agent_name": {"type": "string"},
        "limit":      {"type": "integer", "default": 10},
    },
    "required": ["query"],
}

_TODAY_SCHEMA = {
    "type": "object",
    "properties": {
        "date": {"type": "string", "description": "ISO-Datum (default: heute)"},
    },
}

_TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "from_date":   {"type": "string", "description": "ISO-Datum z.B. '2025-11-01'"},
        "to_date":     {"type": "string", "description": "ISO-Datum (default: heute)"},
        "agent_name":  {"type": "string", "description": "Optional: nur Sessions dieses Agents"},
        "limit":       {"type": "integer", "default": 200, "description": "Max. Sessions"},
    },
    "required": ["from_date"],
}


async def _search(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.db import mirror_query
    q = (args.get("query") or "").strip()
    try:
        results = await mirror_query.search_events(
            q,
            event_type=args.get("event_type") or None,
            agent_name=args.get("agent_name") or None,
            from_date=args.get("from_date") or None,
            to_date=args.get("to_date") or None,
            semantic=False,
            limit=min(int(args.get("limit", 20)), 50),
        )
        return ToolResult.ok(_serialize({"count": len(results), "results": results}))
    except Exception as e:
        return ToolResult.fail(f"Datamining-Suche fehlgeschlagen: {e}")


async def _semantic(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.db import mirror_query
    q = (args.get("query") or "").strip()
    try:
        results = await mirror_query.search_events(
            q,
            event_type=args.get("event_type") or None,
            agent_name=args.get("agent_name") or None,
            semantic=True,
            limit=min(int(args.get("limit", 10)), 30),
        )
        return ToolResult.ok(_serialize({"count": len(results), "results": results}))
    except Exception as e:
        return ToolResult.fail(f"Semantische Suche fehlgeschlagen: {e}")


async def _timeline(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.db import mirror_query
    from datetime import date as _date
    from_date = (args.get("from_date") or "").strip()
    to_date = (args.get("to_date") or "").strip() or _date.today().isoformat()
    limit = min(int(args.get("limit", 200)), 500)
    try:
        sessions = await mirror_query.list_sessions(
            agent_name=args.get("agent_name") or None,
            from_date=from_date,
            to_date=to_date + "T23:59:59",
            limit=limit,
        )
        # Nach Tag gruppieren
        from collections import defaultdict
        by_day: dict = defaultdict(list)
        for s in sessions:
            day = str(s.get("started_at") or s.get("updated_at") or "")[:10]
            by_day[day].append({
                "session_id": s["id"],
                "agent": s.get("agent_name", "?"),
                "user": s.get("username", "?"),
                "events": s.get("event_count", 0),
                "started": str(s.get("started_at") or "")[:16].replace("T", " "),
            })
        days = [{"date": d, "sessions": len(v), "details": v}
                for d, v in sorted(by_day.items(), reverse=True)]
        return ToolResult.ok(_serialize({
            "from_date": from_date, "to_date": to_date,
            "total_sessions": len(sessions), "days": days,
        }))
    except Exception as e:
        return ToolResult.fail(f"Timeline-Abfrage fehlgeschlagen: {e}")


async def _today(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.db import mirror_query
    date = (args.get("date") or "").strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        sessions = await mirror_query.list_sessions(limit=100)
        today = [s for s in sessions if str(s.get("updated_at", ""))[:10] == date]
        return ToolResult.ok(_serialize({"date": date, "sessions": today, "count": len(today)}))
    except Exception as e:
        return ToolResult.fail(f"Today-Abfrage fehlgeschlagen: {e}")


TOOL_SEARCH = Tool(
    name="datamining_search",
    description=(
        "Volltextsuche im Langzeitgedächtnis — alle vergangenen HydraHive-Sessions, "
        "Tool-Calls, Gespräche. Nutze dies um vergangene Entscheidungen, Fehler, "
        "Lösungen oder Ideen wiederzufinden."
    ),
    schema=_SEARCH_SCHEMA,
    execute=_search,
    category="memory",
)

TOOL_SEMANTIC = Tool(
    name="datamining_semantic",
    description=(
        "Semantische Ähnlichkeitssuche im Langzeitgedächtnis — findet inhaltlich Ähnliches "
        "auch ohne exakte Wortübereinstimmung. Ideal für 'Was haben wir zu Thema X besprochen?'"
    ),
    schema=_SEMANTIC_SCHEMA,
    execute=_semantic,
    category="memory",
)

TOOL_TIMELINE = Tool(
    name="datamining_timeline",
    description=(
        "Zeitstrahl aller Sessions in einem Zeitraum, gruppiert nach Tag. "
        "Ideal für Langzeit-Analyse ohne Keyword — z.B. 'was habe ich im November gemacht', "
        "'welche Sessions gab es letzte Woche'. Gibt Themen/Gesprächspartner pro Tag."
    ),
    schema=_TIMELINE_SCHEMA,
    execute=_timeline,
    category="memory",
)

TOOL_TODAY = Tool(
    name="datamining_today",
    description="Übersicht was heute im HydraHive-System passiert ist — Sessions, Anfragen, Tool-Calls.",
    schema=_TODAY_SCHEMA,
    execute=_today,
    category="memory",
)
