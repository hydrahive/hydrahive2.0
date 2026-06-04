from __future__ import annotations

from hydrahive.scratchpad import service
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest das Scratchpad des Users: Tills handgeschriebene Ideen plus deine "
    "eigenen Agent-Notizen. Nutze es, wenn die Aufgabe auf notierte Ideen Bezug nimmt."
)

_SCHEMA = {"type": "object", "properties": {}, "required": []}

_PROMPT_HINT = (
    "\n\nScratchpad: Till hinterlegt hier Ideen und Notizen. Lies sie mit "
    "`read_scratchpad`, wenn die Aufgabe darauf Bezug nimmt. Eigene Notizen "
    "schreibst du mit `write_scratchpad` — nur in deinen Bereich; Tills Bereich ist tabu."
)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult.ok(service.get_combined(ctx.user_id))


TOOL = Tool(
    name="read_scratchpad",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="scratchpad",
    prompt_hint=_PROMPT_HINT,
)
