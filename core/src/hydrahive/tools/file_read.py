from __future__ import annotations

import re

from hydrahive.tools import _fs
from hydrahive.tools._path import PathOutsideWorkspace, read_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult
from hydrahive.tools._errors import fail_with_cause


_DESCRIPTION = (
    "Liest eine Datei aus dem Workspace. Gibt den Inhalt mit Zeilennummern zurück. "
    "Optionen: offset/limit für Zeilenbereiche; grep (Regex) um nur passende Zeilen "
    "zurückzugeben (+ context_lines Zeilen Kontext davor/danach). "
    "Nutze grep wenn du nur bestimmte Werte/Funktionen aus einer großen Datei brauchst — "
    "z.B. grep='secret_key|jwt_algorithm' statt die ganze settings.py zu lesen."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Pfad relativ zum Workspace (oder absolut, muss innerhalb liegen)."},
        "offset": {"type": "integer", "description": "Erste Zeile (1-basiert, optional, ignoriert wenn grep gesetzt).", "default": 1},
        "limit": {"type": "integer", "description": "Anzahl Zeilen (default 2000, ignoriert wenn grep gesetzt).", "default": 2000},
        "grep": {"type": "string", "description": "Regex: gibt nur Zeilen zurück die matchen, plus context_lines Zeilen Kontext."},
        "context_lines": {"type": "integer", "description": "Zeilen Kontext vor/nach jedem grep-Treffer (default 2).", "default": 2},
    },
    "required": ["path"],
}


def _grep_lines(lines: list[str], pattern: str, context: int) -> tuple[str, int]:
    """Returns numbered output with only matching lines + context, and match count."""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Ungültiger Regex: {e}") from e

    total = len(lines)
    include: set[int] = set()
    for i, line in enumerate(lines):
        if regex.search(line):
            for j in range(max(0, i - context), min(total, i + context + 1)):
                include.add(j)

    if not include:
        return "(keine Treffer)", 0

    result: list[str] = []
    prev: int | None = None
    for i in sorted(include):
        if prev is not None and i > prev + 1:
            result.append("   ...\t")
        result.append(f"{i + 1:6d}\t{lines[i]}")
        prev = i

    matches = sum(1 for i, l in enumerate(lines) if regex.search(l))
    return "\n".join(result), matches


async def _read_text(args: dict, ctx: ToolContext) -> tuple[str, str] | ToolResult:
    """(Text, Anzeigepfad) vom Server oder aus dem Projekt-Container (docs/specs/projekt-container-ausfuehrung.md)."""
    path_arg = args.get("path", "")
    try:
        ex = _fs._execution(ctx)
    except _fs.ExecutionUnavailable as e:
        return ToolResult.fail(f"{e.code}: Datei nicht gelesen – Ausführungsort des Projekts nicht verfügbar.")
    if ex["mode"] == "container":
        try:
            path = await _fs.resolve(ex, path_arg, must_exist=True)
            return (await _fs.read_bytes(ex, path)).decode("utf-8", errors="replace"), path
        except FileNotFoundError:
            return ToolResult.fail(f"Datei nicht gefunden: {path_arg}")
        except PathOutsideWorkspace as e:
            return ToolResult.fail(str(e))
        except _fs.ContainerFsError as e:
            return ToolResult.fail(f"Lesefehler: {e}")
    try:
        p = read_path(ctx, path_arg)          # eigener Workspace + verknüpfte Projekte (nur lesen)
    except PathOutsideWorkspace as e:
        return ToolResult.fail(str(e))
    if not p.exists():
        return ToolResult.fail(f"Datei nicht gefunden: {path_arg}")
    if not p.is_file():
        return ToolResult.fail(f"Kein File: {path_arg}")
    try:
        return p.read_text(encoding="utf-8", errors="replace"), str(p)
    except Exception as e:
        return fail_with_cause("Lesefehler", e, "file_read")


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    got = await _read_text(args, ctx)
    if isinstance(got, ToolResult):
        return got
    text, shown = got

    lines = text.splitlines()
    total = len(lines)

    grep_pattern = args.get("grep")
    if grep_pattern:
        context = max(0, min(20, int(args.get("context_lines", 2))))
        try:
            numbered, match_count = _grep_lines(lines, grep_pattern, context)
        except ValueError as e:
            return ToolResult.fail(str(e))
        return ToolResult.ok(numbered, path=shown, total_lines=total, matches=match_count)

    offset = max(1, int(args.get("offset", 1)))
    limit = max(1, min(20000, int(args.get("limit", 2000))))
    start = offset - 1
    end = start + limit
    selected = lines[start:end]
    numbered = "\n".join(f"{i + offset:6d}\t{line}" for i, line in enumerate(selected))
    return ToolResult.ok(numbered, path=shown, total_lines=total, returned_lines=len(selected), truncated=end < total)


TOOL = Tool(name="file_read", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="files")
