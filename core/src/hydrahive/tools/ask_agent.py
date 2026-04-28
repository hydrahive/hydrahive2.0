from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Beauftragt einen anderen Agenten über AgentLink. Stub-Implementierung — "
    "wird beim AgentLink-Service-Ausbau funktional. Aktuell gibt sie eine "
    "Hinweis-Meldung zurück."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "agent_id": {"type": "string", "description": "ID des Ziel-Agenten."},
        "task": {"type": "string", "description": "Aufgabenbeschreibung für den Ziel-Agenten."},
        "context": {"type": "object", "description": "Optionale Zusatz-Daten."},
    },
    "required": ["agent_id", "task"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    target = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    if not target:
        return ToolResult.fail("agent_id fehlt")
    if not task:
        return ToolResult.fail("task fehlt")

    return ToolResult.fail(
        "AgentLink ist noch nicht eingerichtet — ask_agent ist aktuell ein Stub. "
        "Anfrage wäre gewesen: an '" + target + "' mit '" + task[:80] + "'."
    )


TOOL = Tool(name="ask_agent", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
