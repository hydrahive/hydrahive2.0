"""File attachment processing for chat messages."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from fastapi import UploadFile

from hydrahive.tools._path import PathOutsideWorkspace, safe_path

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".csv", ".sh", ".html", ".css", ".xml", ".toml", ".ini", ".cfg",
    ".rs", ".go", ".java", ".c", ".cpp", ".h", ".rb", ".php", ".sql",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_TEXT_BYTES = 100 * 1024          # 100 KB


async def process_upload(file: UploadFile, workspace: Path | None) -> list[dict]:
    """Convert an uploaded file to one or more Anthropic content blocks."""
    data = await file.read()
    name = file.filename or "upload"
    mime = file.content_type or ""
    if not mime or mime == "application/octet-stream":
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    ext = Path(name).suffix.lower()

    if mime in IMAGE_TYPES and len(data) <= MAX_IMAGE_BYTES:
        blocks: list[dict] = [{
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": base64.standard_b64encode(data).decode(),
            },
        }]
        # Bild auch auf Disk speichern damit shell_exec + mmx drankann
        if workspace is not None:
            dest = _safe_dest(workspace, name)
            if dest is None:
                blocks.append({"type": "text", "text": "[Bild-Name abgelehnt: ungültiger Pfad]"})
            else:
                dest.write_bytes(data)
                blocks.append({"type": "text", "text": f"[Bild gespeichert: {dest}]"})
        return blocks

    if ext in TEXT_EXTENSIONS and len(data) <= MAX_TEXT_BYTES:
        try:
            return [{"type": "text", "text": f"[{name}]\n{data.decode('utf-8')}"}]
        except UnicodeDecodeError:
            pass

    # Binary or oversized: save to workspace
    if workspace is not None:
        dest = _safe_dest(workspace, name)
        if dest is None:
            return [{"type": "text", "text": "[Anhang abgelehnt: ungültiger Dateiname]"}]
        dest.write_bytes(data)
        return [{"type": "text", "text": f"[Datei hochgeladen: {dest}]"}]

    return [{"type": "text", "text": f"[Anhang: {name} — kein Workspace verfügbar]"}]


def _safe_dest(workspace: Path, name: str) -> Path | None:
    """Validiert User-Filename gegen Path-Traversal. Wirft None bei Verstoß."""
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        dest = safe_path(workspace, name)
    except PathOutsideWorkspace:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest
