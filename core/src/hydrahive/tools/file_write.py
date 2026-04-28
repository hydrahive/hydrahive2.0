from __future__ import annotations

from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Schreibt eine Datei. Überschreibt vorhandene Inhalte. "
    "Parent-Verzeichnisse werden automatisch angelegt."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Pfad relativ zum Workspace."},
        "content": {"type": "string", "description": "Vollständiger Datei-Inhalt."},
    },
    "required": ["path", "content"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", "")
    content = args.get("content", "")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")

    try:
        p = safe_path(ctx.workspace, path_arg)
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as e:
        return ToolResult.fail(f"Schreibfehler: {e}")

    return ToolResult.ok(
        f"Datei geschrieben: {p}",
        path=str(p),
        bytes=len(content.encode("utf-8")),
        lines=content.count("\n") + 1,
    )


TOOL = Tool(name="file_write", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
