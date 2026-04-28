from __future__ import annotations

from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Liest eine Datei aus dem Workspace. Gibt den Inhalt mit Zeilennummern zurück. "
    "Bei großen Dateien kann mit offset/limit ein Bereich gelesen werden."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Pfad relativ zum Workspace (oder absolut, muss innerhalb liegen)."},
        "offset": {"type": "integer", "description": "Erste Zeile (1-basiert, optional).", "default": 1},
        "limit": {"type": "integer", "description": "Anzahl Zeilen (default 2000).", "default": 2000},
    },
    "required": ["path"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", "")
    try:
        p = safe_path(ctx.workspace, path_arg)
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))

    if not p.exists():
        return ToolResult.fail(f"Datei nicht gefunden: {path_arg}")
    if not p.is_file():
        return ToolResult.fail(f"Kein File: {path_arg}")

    offset = max(1, int(args.get("offset", 1)))
    limit = max(1, min(20000, int(args.get("limit", 2000))))

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return ToolResult.fail(f"Lesefehler: {e}")

    lines = text.splitlines()
    total = len(lines)
    start = offset - 1
    end = start + limit
    selected = lines[start:end]

    numbered = "\n".join(f"{i + offset:6d}\t{line}" for i, line in enumerate(selected))
    truncated = end < total

    return ToolResult.ok(
        numbered,
        path=str(p),
        total_lines=total,
        returned_lines=len(selected),
        truncated=truncated,
    )


TOOL = Tool(name="file_read", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
