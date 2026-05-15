"""query_health_data — Buddy-Tool für Apple Health Auswertung."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest gespeicherte Apple Health Daten (Schritte, Herzfrequenz, Schlaf, Kalorien etc.) "
    "aus dem letzten Zeitraum aus und gibt aggregierte Metriken zurück. "
    "Nutze dieses Tool für Auswertungen und Trends der Gesundheitsdaten."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "integer",
            "description": "Zeitraum in Tagen (default 7, max 365).",
            "default": 7,
        },
        "metric": {
            "type": "string",
            "description": "Optional: Filter auf eine Metrik (z.B. step_count, heart_rate, sleep_analysis).",
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.db import health as health_db
    from hydrahive.settings import settings

    if not settings.health_api_key:
        return ToolResult.fail("Health-Daten nicht konfiguriert (HH_HEALTH_API_KEY fehlt).")

    days = max(1, min(365, int(args.get("days", 7))))
    metric = (args.get("metric") or "").strip() or None

    summary = health_db.get_metrics_summary(days=days, metric=metric)

    if not summary["metrics"]:
        return ToolResult.ok({
            "message": f"Keine Health-Daten für die letzten {days} Tage gefunden.",
            "period_days": days,
        })

    return ToolResult.ok(summary)


TOOL = Tool(
    name="query_health_data",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="personal",
)
