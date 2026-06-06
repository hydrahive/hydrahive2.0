"""task_write — neuen Task anlegen oder bestehenden aktualisieren."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service

_SCHEMA = {
    "type": "object",
    "required": ["title"],
    "properties": {
        "title": {
            "type": "string",
            "description": "Titel des Tasks (kurz und präzise).",
        },
        "description": {
            "type": "string",
            "description": "Optionale Beschreibung / Details.",
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Priorität. Standard: medium.",
        },
        "project_id": {
            "type": "string",
            "description": "Optionale Projekt-ID — verknüpft den Task mit einem Projekt.",
        },
        "task_id": {
            "type": "string",
            "description": "Wenn angegeben: bestehenden Task aktualisieren statt neu anlegen.",
        },
        "status": {
            "type": "string",
            "enum": ["open", "in_progress", "done", "cancelled"],
            "description": "Nur beim Aktualisieren (task_id gesetzt): neuer Status.",
        },
    },
}

_HINT = (
    "Nutze task_write um Aufgaben persistent zu speichern (bleiben über Chat-Sessions erhalten). "
    "Lege einen Task an wenn der User oder du eine Aufgabe identifizierst die erledigt werden soll. "
    "Aktualisiere Tasks mit task_id wenn sich Status oder Inhalt ändern. "
    "Nutze task_list um den aktuellen Stand zu sehen."
)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    task_id: str | None = args.get("task_id")

    if task_id:
        try:
            result = service.update_task(
                username,
                task_id,
                title=args.get("title"),
                description=args.get("description"),
                status=args.get("status"),
                priority=args.get("priority"),
            )
        except ValueError as exc:
            return ToolResult.fail(str(exc))
        if result is None:
            return ToolResult.fail(f"Task {task_id!r} nicht gefunden.")
        return ToolResult.ok({"updated": True, "task": result})

    try:
        task = service.create_task(
            username,
            title=args["title"],
            description=args.get("description", ""),
            priority=args.get("priority", "medium"),
            project_id=args.get("project_id") or ctx.project_id,
            session_id=ctx.session_id,
        )
    except ValueError as exc:
        return ToolResult.fail(str(exc))

    return ToolResult.ok({"created": True, "task": task})


TOOL = Tool(
    name="task_write",
    description=(
        "Legt einen neuen persistenten Task an oder aktualisiert einen bestehenden. "
        "Tasks bleiben über alle Chat-Sessions erhalten."
    ),
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
    prompt_hint=_HINT,
)
