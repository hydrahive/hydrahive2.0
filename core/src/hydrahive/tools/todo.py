from __future__ import annotations

from hydrahive.db import session_state
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Schreibt die Todo-Liste der Session komplett neu. Der Agent gibt jedes Mal "
    "die volle Liste — sie ersetzt die vorherige. Status: pending | in_progress | done."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "Liste von Todo-Einträgen.",
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Beschreibung der Aufgabe."},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "done"],
                        "default": "pending",
                    },
                },
                "required": ["content"],
            },
        },
    },
    "required": ["items"],
}

_VALID_STATUS = {"pending", "in_progress", "done"}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    items = args.get("items")
    if not isinstance(items, list):
        return ToolResult.fail("items muss eine Liste sein")

    cleaned: list[dict] = []
    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            return ToolResult.fail(f"Eintrag {i} ist kein Objekt")
        content = (raw.get("content") or "").strip()
        if not content:
            return ToolResult.fail(f"Eintrag {i}: content fehlt")
        status = raw.get("status", "pending")
        if status not in _VALID_STATUS:
            return ToolResult.fail(f"Eintrag {i}: status '{status}' ungültig")
        cleaned.append({"content": content, "status": status})

    session_state.set(ctx.session_id, "todos", cleaned)
    counts = {s: sum(1 for c in cleaned if c["status"] == s) for s in _VALID_STATUS}
    return ToolResult.ok({"items": cleaned, "count": len(cleaned), "by_status": counts})


TOOL = Tool(name="todo_write", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
