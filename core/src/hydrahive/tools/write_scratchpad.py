from __future__ import annotations

from hydrahive.scratchpad import service
from hydrahive.scratchpad.service import ScratchpadTooLarge
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Schreibt in DEINE Agent-Notiz-Zone des Scratchpads (ersetzt sie komplett). "
    "Tills eigener Bereich ist tabu und kann hierüber nicht verändert werden. "
    "Lies vorher mit read_scratchpad, damit du deine bestehenden Notizen nicht verlierst."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Vollständiger neuer Inhalt deiner Agent-Zone (Markdown).",
        },
    },
    "required": ["content"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    content = args.get("content")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")
    try:
        service.save_agent(ctx.user_id, content)
    except ScratchpadTooLarge as e:
        return ToolResult.fail(str(e))
    return ToolResult.ok("Agent-Notizen gespeichert.")


TOOL = Tool(
    name="write_scratchpad",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="scratchpad",
)
