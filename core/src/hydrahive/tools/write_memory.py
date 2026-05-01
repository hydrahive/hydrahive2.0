from __future__ import annotations

from hydrahive.tools._memory_store import delete_key, write_key
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Speichert eine Memory-Notiz unter dem angegebenen Schlüssel. "
    "Mit `delete=true` wird der Eintrag entfernt."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {"type": "string", "description": "Memory-Schlüssel (z.B. 'projekt.notizen')."},
        "content": {"type": "string", "description": "Inhalt der Notiz."},
        "delete": {"type": "boolean", "description": "Eintrag löschen statt schreiben.", "default": False},
    },
    "required": ["key"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    key = (args.get("key") or "").strip()
    if not key:
        return ToolResult.fail("Leerer key")

    if args.get("delete"):
        existed = delete_key(ctx.agent_id, key)
        if not existed:
            return ToolResult.fail(f"Memory-Eintrag '{key}' existiert nicht")
        return ToolResult.ok(f"Memory '{key}' gelöscht")

    content = args.get("content")
    if content is None:
        return ToolResult.fail("content fehlt")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")

    write_key(ctx.agent_id, key, content)
    return ToolResult.ok(f"Memory '{key}' gespeichert", key=key, bytes=len(content.encode("utf-8")))


TOOL = Tool(name="write_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="memory")
