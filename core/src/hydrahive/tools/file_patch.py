from __future__ import annotations

from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Ändert eine bestehende Datei durch String-Ersetzung. `old_string` muss "
    "im File eindeutig sein — sonst Fehler. Mit `replace_all=true` werden alle "
    "Vorkommen ersetzt. Liest die Datei vorher (kein Reset von fremdem Code)."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Pfad zur Datei (im Workspace)."},
        "old_string": {"type": "string", "description": "Text der ersetzt wird. Muss eindeutig sein (außer replace_all)."},
        "new_string": {"type": "string", "description": "Neuer Text."},
        "replace_all": {"type": "boolean", "description": "Alle Vorkommen ersetzen (default false).", "default": False},
    },
    "required": ["path", "old_string", "new_string"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", "")
    old = args.get("old_string", "")
    new = args.get("new_string", "")
    replace_all = bool(args.get("replace_all", False))

    if not old:
        return ToolResult.fail("old_string darf nicht leer sein")
    if old == new:
        return ToolResult.fail("old_string und new_string sind identisch")

    try:
        p = safe_path(ctx.workspace, path_arg)
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))

    if not p.is_file():
        return ToolResult.fail(f"Datei nicht gefunden: {path_arg}")

    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return ToolResult.fail(f"Lesefehler: {e}")

    count = text.count(old)
    if count == 0:
        return ToolResult.fail("old_string nicht in der Datei gefunden")
    if count > 1 and not replace_all:
        return ToolResult.fail(
            f"old_string kommt {count}× vor — entweder Kontext erweitern oder replace_all=true"
        )

    new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    try:
        p.write_text(new_text, encoding="utf-8")
    except Exception as e:
        return ToolResult.fail(f"Schreibfehler: {e}")

    return ToolResult.ok(
        f"Datei gepatcht: {p}",
        path=str(p),
        replacements=count if replace_all else 1,
    )


TOOL = Tool(name="file_patch", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
