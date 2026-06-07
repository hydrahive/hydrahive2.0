"""task_read — einzelnen Task per ID abrufen."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service

_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "ID des Tasks (vollständig oder die ersten 8 Zeichen).",
        },
    },
    "required": ["task_id"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    task_id = args["task_id"].strip()
    task = service.get_task(username, task_id)

    if task is None:
        # Kurzform-Suche: task_id könnte ein 8-Zeichen-Prefix sein
        all_tasks = service.list_tasks(username)
        matches = [t for t in all_tasks if t["id"].startswith(task_id)]
        if len(matches) == 1:
            task = matches[0]
        elif len(matches) > 1:
            ids = ", ".join(t["id"][:8] for t in matches)
            return ToolResult.fail(f"Mehrdeutig — {len(matches)} Tasks beginnen mit '{task_id}': {ids}")
        else:
            return ToolResult.fail(f"Task '{task_id}' nicht gefunden.")

    status_icon = {"open": "○", "in_progress": "◑", "done": "●", "cancelled": "✗"}.get(task["status"], "?")
    lines = [
        f"{status_icon} {task['title']}",
        f"ID:       {task['id']}",
        f"Status:   {task['status']}",
        f"Priorität: {task['priority']}",
    ]
    if task.get("description"):
        lines.append(f"Beschreibung: {task['description']}")
    if task.get("project_id"):
        lines.append(f"Projekt:  {task['project_id']}")
    lines.append(f"Erstellt: {task['created_at']}")
    lines.append(f"Geändert: {task['updated_at']}")

    return ToolResult.ok({"task": task, "summary": "\n".join(lines)})


TOOL = Tool(
    name="task_read",
    description=(
        "Liest einen einzelnen Task per ID (vollständig oder 8-Zeichen-Prefix). "
        "Nützlich wenn die ID aus einem vorherigen task_write bekannt ist."
    ),
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
)
