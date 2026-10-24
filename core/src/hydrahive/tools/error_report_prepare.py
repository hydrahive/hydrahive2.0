"""Hilfe-Assistent: Fehlerbericht vorbereiten (docs/plans/help-error-report.md). Sendet NIE.

Sammelt die echten Fehlerdaten serverseitig (helpdesk/_report.build) und legt einen Entwurf an. Der Nutzer sieht ihn im
Hilfe-Fenster und schickt ihn dort mit „Senden“ ab. Die Seite kommt vom Hilfe-Fenster, nicht vom Modell.
"""
from __future__ import annotations

from hydrahive.helpdesk import _report
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Bereitet einen Fehlerbericht an das HydraHive-Team vor. Nutze das, wenn der Nutzer einen Fehler meldet "
    "(etwas geht nicht, Fehlermeldung, Absturz). Der Bericht enthält automatisch die echten Fehlerdaten dieser "
    "Installation (Fehlerprotokoll des Nutzers, Seite, Versionen). Du gibst nur eine kurze, sachliche Beschreibung "
    "in den Worten des Nutzers mit. Das Werkzeug SENDET NICHT: Der Nutzer prüft den Bericht im Hilfe-Fenster und "
    "klickt selbst auf „Senden“."
)
_SCHEMA = {
    "type": "object",
    "properties": {"description": {"type": "string",
                                   "description": "Was der Nutzer gemacht hat und was passiert ist (höchstens "
                                                  "1000 Zeichen)."}},
    "required": ["description"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    if not _report.enabled():
        return ToolResult.fail("Fehlerberichte sind auf dieser Installation ausgeschaltet (Admin: "
                               "System → Einstellungen → Hilfe).")
    desc = str(args.get("description") or "").strip()
    if not desc:
        return ToolResult.fail("description fehlt: kurz beschreiben, was der Nutzer gemacht hat und was passiert ist")
    d = _report.prepare(ctx.user_id, desc, _report.page_for(ctx.session_id))
    return ToolResult.ok({
        "report_id": d["id"], "subject": d["subject"], "to": _report.recipient(),
        "errors_found": d["errors"],
        "next": "Der Bericht liegt im Hilfe-Fenster. Bitte den Nutzer, ihn zu prüfen und auf „Senden“ zu klicken.",
    }, report_id=d["id"])


TOOL = Tool(name="error_report_prepare", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute,
            category="help")
