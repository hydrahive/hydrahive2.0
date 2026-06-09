"""task_list — Tasks abfragen."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service

_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["open", "in_progress", "done", "cancelled"],
            "description": "Optional: nach Status filtern. Ohne Filter: alle Tasks.",
        },
        "project_id": {
            "type": "string",
            "description": "Optional: nur Tasks des angegebenen Projekts.",
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    # Wie task_write: ctx.project_id als Standard-Filter, explizites Argument hat Vorrang.
    project_id = args.get("project_id") or ctx.project_id or None

    tasks = service.list_tasks(
        username,
        status=args.get("status"),
        project_id=project_id,
    )

    if not tasks:
        return ToolResult.ok({"count": 0, "tasks": [], "message": "Keine Tasks gefunden."})

    lines = []
    for t in tasks:
        status_icon = {"open": "○", "in_progress": "◑", "done": "●", "cancelled": "✗"}.get(t["status"], "?")
        prio_tag = {"high": "[!]", "medium": "", "low": "[~]"}.get(t["priority"], "")
        desc = f" — {t['description'][:80]}" if t.get("description") else ""
        lines.append(f"{status_icon} [{t['id'][:8]}] {prio_tag}{t['title']}{desc}")

    return ToolResult.ok({"count": len(tasks), "tasks": tasks, "summary": "\n".join(lines)})


TOOL = Tool(
    name="task_list",
    description="Listet persistente Tasks des Users auf. Optional nach Status oder Projekt filtern.",
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
)
