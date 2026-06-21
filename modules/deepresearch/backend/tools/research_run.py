"""deep_research — gründliche Web-Recherche, liefert einen zitierten Bericht.

Blockiert bis der Lauf fertig ist (bis ~max_time im Loop), damit der Agent das
Ergebnis direkt verwenden kann. Den hübschen HTML-Report holt der Mensch über
report_url (Phase 2).
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service

_SCHEMA = {
    "type": "object",
    "required": ["question"],
    "properties": {
        "question": {
            "type": "string",
            "description": "Die Recherche-Frage / das Thema (präzise formulieren).",
        },
        "model": {
            "type": "string",
            "description": "Optional: Modell-ID für die Recherche (sonst Default-Modell).",
        },
    },
}

_HINT = """
Nutze deep_research, wenn der Nutzer eine gründliche, quellenbasierte Recherche oder
einen Bericht zu einem Thema will ("recherchiere", "mach mir einen Überblick/Bericht
über", "was gibt es Neues zu …", Vergleich/Kaufberatung/Faktencheck mit Belegen).

NICHT nutzen für einfache Fragen, die du direkt beantworten kannst, oder wenn nur eine
einzelne aktuelle Zahl gesucht ist (dann web_search). Der Lauf dauert Minuten.
"""


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    question = (args.get("question") or "").strip()
    if not question:
        return ToolResult.fail("Keine Frage angegeben.")
    if not ctx.user_id:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    run = await service.run_blocking(ctx.user_id, question, args.get("model") or None)
    if run["status"] == "error":
        return ToolResult.fail(f"Recherche fehlgeschlagen: {run.get('error') or 'unbekannter Fehler'}")

    result = run.get("result") or {}
    # ponytail: gibt den vollen Markdown-Report zurück (in Phase 1 gibt es noch keinen
    # Viewer). Auf Zusammenfassung+URL umstellen, sobald der HTML-Report (Phase 2) steht.
    return ToolResult.ok({
        "run_id": run["id"],
        "report_url": f"/api/modules/deepresearch/runs/{run['id']}/report",
        "stats": result.get("stats", {}),
        "sources": result.get("sources", []),
        "report_markdown": result.get("markdown", ""),
    })


TOOL = Tool(
    name="deep_research",
    description=(
        "Führt eine mehrstufige Web-Recherche durch (Plan → Suche → Synthese) und liefert "
        "einen zitierten Markdown-Bericht mit Quellen. Dauert Minuten."
    ),
    schema=_SCHEMA,
    execute=_execute,
    category="research",
    prompt_hint=_HINT,
)
