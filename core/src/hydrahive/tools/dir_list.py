from __future__ import annotations

from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Listet den Inhalt eines Verzeichnisses. Mit recursive=true wird der "
    "ganze Baum durchlaufen (max. 500 Einträge)."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Verzeichnis (optional, default Workspace-Root).", "default": ""},
        "recursive": {"type": "boolean", "description": "Rekursiv durchlaufen.", "default": False},
    },
}

_MAX_ENTRIES = 500
_SKIP = {".git", "__pycache__", "node_modules", ".venv", ".tox", ".mypy_cache"}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    sub = args.get("path", "")
    recursive = bool(args.get("recursive", False))

    try:
        root = safe_path(ctx.workspace, sub) if sub else ctx.workspace.resolve()
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))
    if not root.is_dir():
        return ToolResult.fail(f"Kein Verzeichnis: {sub or '.'}")

    entries: list[dict] = []
    truncated = False
    iterator = root.rglob("*") if recursive else root.iterdir()
    for p in iterator:
        if any(part in _SKIP for part in p.parts):
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        rel = str(p.relative_to(ctx.workspace))
        entries.append({
            "path": rel,
            "type": "dir" if p.is_dir() else "file",
            "size": stat.st_size if p.is_file() else None,
        })
        if len(entries) >= _MAX_ENTRIES:
            truncated = True
            break

    entries.sort(key=lambda e: (e["type"] != "dir", e["path"]))
    return ToolResult.ok({"entries": entries, "count": len(entries), "truncated": truncated})


TOOL = Tool(name="dir_list", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
