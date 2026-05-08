from __future__ import annotations

from hydrahive.tools._memory_store import delete_key, write_key
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Speichert eine Memory-Notiz unter dem angegebenen Schlüssel. "
    "Mit `delete=true` wird der Eintrag entfernt. "
    "Mit `expires_at` verfällt der Eintrag automatisch (+2h, +1d, +7d, +4w oder ISO-Timestamp)."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "Memory-Schlüssel (z.B. 'projekt.notizen').",
        },
        "content": {
            "type": "string",
            "description": "Inhalt der Notiz.",
        },
        "delete": {
            "type": "boolean",
            "description": "Eintrag löschen statt schreiben.",
            "default": False,
        },
        "expires_at": {
            "type": "string",
            "description": (
                "Ablaufzeit: relative Angabe (+2h, +1d, +7d, +4w) oder ISO-Timestamp. "
                "Nach Ablauf wird der Eintrag bei Lesezugriffen ignoriert. "
                "Nützlich für temporäre Informationen (Status, laufende Deploys, WIP-Branches)."
            ),
        },
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

    expires_at = args.get("expires_at")
    entry = write_key(ctx.agent_id, key, content, expires_at=expires_at or None)

    extra = {}
    if entry.get("expires_at"):
        extra["expires_at"] = entry["expires_at"]

    return ToolResult.ok(
        f"Memory '{key}' gespeichert",
        key=key,
        bytes=len(content.encode("utf-8")),
        **extra,
    )


TOOL = Tool(name="write_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="memory")
