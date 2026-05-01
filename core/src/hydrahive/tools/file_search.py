from __future__ import annotations

import re
from pathlib import Path

from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Sucht Dateien per Glob-Pattern und optional Inhalt per Regex. "
    "Beispiele: pattern='**/*.py', content='def main'. Begrenzt auf 200 Treffer."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {"type": "string", "description": "Glob-Pattern für Dateinamen (z.B. '**/*.py').", "default": "**/*"},
        "content": {"type": "string", "description": "Optionaler Regex der im File-Inhalt suchen soll."},
        "path": {"type": "string", "description": "Unterverzeichnis (optional, default Workspace-Root)."},
        "max_results": {"type": "integer", "description": "Maximum (default 200).", "default": 200},
    },
}

_MAX_FILE_SIZE = 2_000_000


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    pattern = args.get("pattern", "**/*") or "**/*"
    content_re = args.get("content")
    sub = args.get("path", "")
    max_results = max(1, min(2000, int(args.get("max_results", 200))))

    try:
        root = safe_path(ctx.workspace, sub) if sub else ctx.workspace.resolve()
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))
    if not root.is_dir():
        return ToolResult.fail(f"Kein Verzeichnis: {sub or '.'}")

    try:
        regex = re.compile(content_re) if content_re else None
    except re.error as e:
        return ToolResult.fail(f"Ungültiger Regex: {e}")

    hits: list[dict] = []
    for p in root.glob(pattern):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ctx.workspace))
        if regex is None:
            hits.append({"path": rel})
        else:
            try:
                if p.stat().st_size > _MAX_FILE_SIZE:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            matches = []
            for ln, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append({"line": ln, "text": line.rstrip()[:300]})
                    if len(matches) >= 20:
                        break
            if matches:
                hits.append({"path": rel, "matches": matches})
        if len(hits) >= max_results:
            break

    return ToolResult.ok(
        {"hits": hits, "count": len(hits), "truncated": len(hits) >= max_results},
    )


TOOL = Tool(name="file_search", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="files")
