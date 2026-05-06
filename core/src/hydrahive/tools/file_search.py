from __future__ import annotations

import re
from pathlib import Path

from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Sucht Dateien per Glob-Pattern und/oder Inhalt per Regex. "
    "Zwei Anwendungsfälle: "
    "(1) Dateien finden: pattern='**/*.py', content='def main' — gibt Pfade + Treffer-Zeilen zurück. "
    "(2) Innerhalb einer bekannten Datei suchen: path='core/src/hydrahive/settings/settings.py', "
    "content='secret_key|jwt_algorithm' — gibt nur die passenden Zeilen zurück. "
    "Nutze content-Suche statt file_read wenn du nur bestimmte Werte aus einer Datei brauchst."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {"type": "string", "description": "Glob-Pattern für Dateinamen (z.B. '**/*.py'). Optional wenn path eine Datei ist.", "default": "**/*"},
        "content": {"type": "string", "description": "Regex der im Datei-Inhalt suchen soll. Gibt Zeile + Zeilennummer zurück."},
        "path": {"type": "string", "description": "Pfad zu Datei oder Verzeichnis (optional, default Workspace-Root). Wenn eine Datei angegeben wird, wird nur diese durchsucht."},
        "max_results": {"type": "integer", "description": "Maximum Treffer (default 200).", "default": 200},
    },
}

_MAX_FILE_SIZE = 2_000_000


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    pattern = args.get("pattern", "**/*") or "**/*"
    content_re = args.get("content")
    sub = args.get("path", "")
    max_results = max(1, min(2000, int(args.get("max_results", 200))))

    try:
        target = safe_path(ctx.workspace, sub) if sub else ctx.workspace.resolve()
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))

    try:
        regex = re.compile(content_re) if content_re else None
    except re.error as e:
        return ToolResult.fail(f"Ungültiger Regex: {e}")

    # Einzelne Datei direkt durchsuchen
    if target.is_file():
        if regex is None:
            return ToolResult.ok({"hits": [{"path": str(target.relative_to(ctx.workspace))}], "count": 1, "truncated": False})
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return ToolResult.fail(str(e))
        rel = str(target.relative_to(ctx.workspace))
        matches = []
        for ln, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                matches.append({"line": ln, "text": line.rstrip()[:300]})
        hits = [{"path": rel, "matches": matches}] if matches else []
        return ToolResult.ok({"hits": hits, "count": len(matches), "truncated": False})

    if not target.is_dir():
        return ToolResult.fail(f"Nicht gefunden: {sub or '.'}")

    hits: list[dict] = []
    for p in target.glob(pattern):
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
