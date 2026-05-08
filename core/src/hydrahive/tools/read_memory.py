from __future__ import annotations

from hydrahive.tools._memory_store import _is_expired, list_keys, load, read_key
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Liest die eigenen Memory-Notizen des Agenten. Ohne `key` wird die Liste "
    "aller Schlüssel zurückgegeben. Mit `key` der Inhalt dieses Eintrags. "
    "Abgelaufene Einträge werden automatisch ausgeblendet."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "Memory-Schlüssel (optional).",
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    key = args.get("key")

    if not key:
        keys = list_keys(ctx.agent_id)
        return ToolResult.ok({"keys": keys, "count": len(keys)})

    # Rohen Entry holen um Ablauf-Info zurückgeben zu können
    data = load(ctx.agent_id)
    entry = data.get(key)

    if entry is None:
        return ToolResult.fail(f"Kein Memory-Eintrag für '{key}'")

    if _is_expired(entry):
        return ToolResult.fail(
            f"Memory-Eintrag '{key}' ist abgelaufen (expires_at: {entry.get('expires_at')})"
        )

    result: dict = {"key": key, "content": entry.get("content")}
    if entry.get("expires_at"):
        result["expires_at"] = entry["expires_at"]
    if entry.get("created_at"):
        result["created_at"] = entry["created_at"]
    if entry.get("updated_at"):
        result["updated_at"] = entry["updated_at"]

    return ToolResult.ok(result)


TOOL = Tool(name="read_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="memory")
