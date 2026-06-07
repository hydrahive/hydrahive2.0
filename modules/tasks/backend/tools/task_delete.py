"""task_delete — Task endgültig löschen."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service

_SCHEMA = {
    "type": "object",
    "required": ["task_id"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "ID des Tasks (vollständig oder 8-Zeichen-Prefix).",
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    task_id = args["task_id"].strip()

    # Kurzform-Suche
    if len(task_id) < 36:
        all_tasks = service.list_tasks(username)
        matches = [t for t in all_tasks if t["id"].startswith(task_id)]
        if len(matches) == 1:
            task_id = matches[0]["id"]
        elif len(matches) > 1:
            ids = ", ".join(t["id"][:8] for t in matches)
            return ToolResult.fail(f"Mehrdeutig — {len(matches)} Tasks beginnen mit '{task_id}': {ids}")

    if not service.delete_task(username, task_id):
        return ToolResult.fail(f"Task '{task_id}' nicht gefunden.")

    return ToolResult.ok({"deleted": True, "task_id": task_id})


TOOL = Tool(
    name="task_delete",
    description="Löscht einen Task endgültig. Verwende dies wenn ein Task nicht mehr gebraucht wird.",
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
)
