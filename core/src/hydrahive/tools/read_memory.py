from __future__ import annotations

from hydrahive.tools._memory_store import list_keys, read_entry
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Liest die eigenen Memory-Notizen des Agenten. Ohne `key` wird die Liste "
    "aller Schlüssel zurückgegeben — gefiltert nach aktivem Projekt + globalen Einträgen. "
    "Mit `key` wird der Eintrag direkt gelesen (kein Projekt-Filter). "
    "Mit `project='*'` werden alle Projekte aufgelistet. "
    "Abgelaufene und veraltete Einträge werden ausgeblendet."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "Memory-Schlüssel (optional).",
        },
        "project": {
            "type": "string",
            "description": (
                "Projekt-Filter für die Key-Liste (nur ohne `key`). "
                "'*' für alle Projekte. Default: aktives Projekt + globale."
            ),
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    key = args.get("key")

    if not key:
        filter_project = args.get("project") or None
        keys = list_keys(
            ctx.agent_id,
            filter_project=filter_project,
            active_project=ctx.project_id,
        )
        return ToolResult.ok({"keys": keys, "count": len(keys)})

    entry = read_entry(ctx.agent_id, key)

    if entry is None:
        return ToolResult.fail(f"Kein Memory-Eintrag für '{key}' (nicht vorhanden oder abgelaufen)")

    result: dict = {
        "key": key,
        "content": entry.get("content"),
        "confidence": entry.get("confidence", 0.5),
        "reinforcements": entry.get("reinforcements", 0),
        "is_latest": entry.get("is_latest", True),
    }
    if entry.get("project"):
        result["project"] = entry["project"]
    if entry.get("expires_at"):
        result["expires_at"] = entry["expires_at"]
    if entry.get("last_reinforced_at"):
        result["last_reinforced_at"] = entry["last_reinforced_at"]
    if entry.get("created_at"):
        result["created_at"] = entry["created_at"]
    if entry.get("updated_at"):
        result["updated_at"] = entry["updated_at"]
    if not entry.get("is_latest", True) and entry.get("superseded_by"):
        result["superseded_by"] = entry["superseded_by"]

    return ToolResult.ok(result)


TOOL = Tool(name="read_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="memory")
