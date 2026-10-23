"""Hilfe-Assistent: Handbuch nach Wörtern durchsuchen (docs/plans/help-assistant.md)."""
from __future__ import annotations

from hydrahive.helpdesk import _manual as manual
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Durchsucht das HydraHive-Handbuch (alle Hilfe-Artikel + Benutzerhandbuch) nach Wörtern. Liefert passende "
    "Abschnitte mit Thema (topic), Überschrift und Auszug. Danach mit help_read(topic) den ganzen Artikel lesen. "
    "Mehrere kurze Suchwörter funktionieren besser als ein langer Satz."
)
_SCHEMA = {
    "type": "object",
    "properties": {"query": {"type": "string", "description": "Suchwörter, z. B. „Agent anlegen“"}},
    "required": ["query"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    query = str(args.get("query") or "").strip()
    if not query:
        return ToolResult.fail("query fehlt")
    lang = str((ctx.config or {}).get("help_lang") or "de")
    hits = manual.search(query[:200], lang)
    out: dict = {"hits": hits}
    if not hits:
        out["topics"] = manual.topics(lang)
    return ToolResult.ok(out)


TOOL = Tool(name="help_search", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="help")
