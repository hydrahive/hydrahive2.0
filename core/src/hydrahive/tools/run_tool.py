"""run_tool – ein beliebiges freigegebenes Werkzeug über seinen Namen aufrufen (Katalog, Spec E4).

``execute`` wird NIE direkt erreicht: Der Runner packt den Aufruf in ``runner/_run_tool_unwrap.py`` aus, bevor Bestätigung,
Vault-Sperre, Freigabe und Dispatcher laufen. Das Tool steht in der Registry, ist aber in keiner Agenten-Config und keiner
Standard-Liste eingetragen; freigeschaltet wird es erst im Katalog-Modus (``tool_mode: catalog``).
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Ruft ein freigegebenes Werkzeug über seinen Namen auf, auch wenn es nicht in deiner Liste steht. "
    "Den Namen und die Felder liefert find_tools. Es gelten dieselben Freigaben und Bestätigungen wie bei einem "
    "direkten Aufruf; ein nicht freigegebenes Werkzeug wird abgelehnt."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Name des Werkzeugs (aus find_tools)."},
        "args": {"type": "object", "description": "Argumente für dieses Werkzeug, genau wie das Schema aus find_tools."},
    },
    "required": ["name"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    # Nicht erreichbar, solange der Runner auspackt. Fail-closed, falls doch jemand direkt dispatcht.
    return ToolResult.fail("run_tool wird vom Runner ausgepackt und lässt sich nicht direkt ausführen.")


TOOL = Tool(name="run_tool", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="catalog")
