from __future__ import annotations

from hydrahive.tools._memory_store import list_keys, load, read_key
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Liest die eigenen Memory-Notizen des Agenten. Ohne `key` wird die Liste "
    "aller Schlüssel zurückgegeben. Mit `key` der Inhalt dieses Eintrags."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {"type": "string", "description": "Memory-Schlüssel (optional)."},
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    key = args.get("key")
    if not key:
        keys = list_keys(ctx.agent_id)
        return ToolResult.ok({"keys": keys, "count": len(keys)})

    content = read_key(ctx.agent_id, key)
    if content is None:
        return ToolResult.fail(f"Kein Memory-Eintrag für '{key}'")
    return ToolResult.ok({"key": key, "content": content})


TOOL = Tool(name="read_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
