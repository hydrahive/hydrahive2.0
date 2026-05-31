from __future__ import annotations

from hydrahive.scratchpad import service
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest das Scratchpad des Users: Tills handgeschriebene Ideen plus deine "
    "eigenen Agent-Notizen. Nutze es, wenn die Aufgabe auf notierte Ideen Bezug nimmt."
)

_SCHEMA = {"type": "object", "properties": {}, "required": []}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult.ok(service.get_combined(ctx.user_id))


TOOL = Tool(
    name="read_scratchpad",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="scratchpad",
)
