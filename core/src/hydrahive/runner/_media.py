"""Extract media file paths from ToolResult.

Sucht deterministisch (KEIN LLM!) in Tool-Outputs nach Datei-Pfaden, die
zu Bild/Audio/Video-Dateien zeigen, normalisiert sie auf absolute Pfade
relativ zum Workspace und liefert eine flache Media-Liste, die als
zusätzliches Feld in den `tool_result`-Block gehängt wird.

Frontend rendert direkt aus dieser Liste — kein LLM-Antworttext-Parsing
mehr.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hydrahive.tools.base import ToolResult

IMG_EXT = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "avif"}
AUD_EXT = {"mp3", "ogg", "wav", "m4a", "opus", "flac"}
VID_EXT = {"mp4", "webm", "mov", "m3u8"}

from hydrahive.settings import settings

# Absoluter Pfad mit Endung, in beliebigem Text.
ABS_PATH_RE = re.compile(
    r"(/(?:tmp|var/lib/hydrahive2)/[^\s`)\"'\],}<>|]+\.(?:"
    + "|".join(sorted(IMG_EXT | AUD_EXT | VID_EXT))
    + r"))",
    re.IGNORECASE,
)


def _kind(path: str) -> str | None:
    ext = Path(path).suffix.lower().lstrip(".")
    if ext in IMG_EXT:
        return "image"
    if ext in AUD_EXT:
        return "audio"
    if ext in VID_EXT:
        return "video"
    return None


def _resolve(path: str, workspace: Path | None) -> str | None:
    """Macht relative Pfade absolut über workspace, prüft Serve-Whitelist."""
    p = Path(path)
    if not p.is_absolute():
        if workspace is None:
            return None
        p = (workspace / p).resolve()
    s = str(p)
    if not s.startswith(settings.servable_prefixes):
        return None
    return s


def _walk_strings(value: Any):
    """Yieldet alle Strings in einem nested dict/list."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_strings(v)


def _candidates_from_output(output: Any) -> list[str]:
    """Sammelt Pfad-Kandidaten aus dict-Feldern UND aus eingebettetem JSON."""
    out: list[str] = []
    if isinstance(output, dict):
        if isinstance(output.get("output_file"), str):
            out.append(output["output_file"])
        for s in output.get("saved") or []:
            if isinstance(s, str):
                out.append(s)
        for s in output.get("all_files") or []:
            if isinstance(s, str):
                out.append(s)
    # Plus regex-scan aller String-Werte (fängt z.B. shell_exec stdout
    # mit `{"saved":["foo.jpg"]}` ein).
    for s in _walk_strings(output):
        out.extend(ABS_PATH_RE.findall(s))
        # Auch eingebettetes JSON parsen
        if "saved" in s and "{" in s:
            try:
                data = json.loads(s.strip())
                for fn in (data.get("saved") if isinstance(data, dict) else None) or []:
                    if isinstance(fn, str):
                        out.append(fn)
            except (json.JSONDecodeError, ValueError):
                pass
    return out


def extract_media(result: ToolResult, workspace: Path | None) -> list[dict]:
    """Liefert [{kind, path}, ...] für alle Media-Files im Tool-Result.

    workspace: für relative Pfade aus shell_exec (z.B. wenn mmx ohne
    --out-dir aufgerufen wird und nur 'image_001.jpg' rauskommt).
    """
    if not result.success:
        return []
    media: list[dict] = []
    seen: set[str] = set()
    for cand in _candidates_from_output(result.output):
        resolved = _resolve(cand, workspace)
        if not resolved or resolved in seen:
            continue
        kind = _kind(resolved)
        if not kind:
            continue
        seen.add(resolved)
        media.append({"kind": kind, "path": resolved})
    return media
