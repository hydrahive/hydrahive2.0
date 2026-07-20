"""File attachment processing for chat messages."""
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from uuid import uuid4

import anyio
from fastapi import UploadFile

from hydrahive.tools._path import PathOutsideWorkspace, safe_path

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".csv", ".sh", ".html", ".css", ".xml", ".toml", ".ini", ".cfg",
    ".rs", ".go", ".java", ".c", ".cpp", ".h", ".rb", ".php", ".sql",
}
MAX_FILES = 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024       # 5 MiB inline zum LLM
MAX_TEXT_BYTES = 100 * 1024             # 100 KiB inline zum LLM
MAX_FILE_BYTES = 100 * 1024 * 1024      # 100 MiB pro Anhang
MAX_MESSAGE_UPLOAD_BYTES = 200 * 1024 * 1024
STREAM_CHUNK_BYTES = 1024 * 1024         # 1 MiB, kein Voll-Read für Binaries


class UploadTooLarge(ValueError):
    def __init__(
        self,
        scope: str,
        max_bytes: int,
        actual_bytes: int,
        filename: str | None = None,
    ) -> None:
        self.scope = scope
        self.max_bytes = max_bytes
        self.actual_bytes = actual_bytes
        self.filename = filename
        super().__init__(f"upload {scope} exceeds {max_bytes} bytes")


class UploadSizeUnknown(ValueError):
    pass


class UploadTooManyFiles(ValueError):
    pass


def validate_upload_sizes(files: list[UploadFile]) -> None:
    """Verteidigung gegen umgangene Client-Limits vor jedem Disk-Write."""
    if len(files) > MAX_FILES:
        raise UploadTooManyFiles
    total = 0
    for file in files:
        if file.size is None:
            raise UploadSizeUnknown(file.filename or "upload")
        if file.size > MAX_FILE_BYTES:
            raise UploadTooLarge(
                "file", MAX_FILE_BYTES, file.size, file.filename or "upload",
            )
        total += file.size
    if total > MAX_MESSAGE_UPLOAD_BYTES:
        raise UploadTooLarge("message", MAX_MESSAGE_UPLOAD_BYTES, total)


async def process_upload(file: UploadFile, workspace: Path | None) -> list[dict]:
    """Konvertiert kleine Inhalte; streamt größere/binäre Dateien in den Workspace."""
    name = file.filename or "upload"
    mime = file.content_type or ""
    if not mime or mime == "application/octet-stream":
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    ext = Path(name).suffix.lower()

    if file.size is not None and file.size > MAX_FILE_BYTES:
        raise UploadTooLarge("file", MAX_FILE_BYTES, file.size, name)

    if mime in IMAGE_TYPES:
        data = await _read_limited(file, MAX_IMAGE_BYTES)
        if data is not None:
            blocks: list[dict] = [{
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.standard_b64encode(data).decode(),
                },
            }]
            if workspace is not None:
                dest = _safe_dest(workspace, name)
                if dest is None:
                    blocks.append({"type": "text", "text": "[Bild-Name abgelehnt: ungültiger Pfad]"})
                else:
                    await _write_small_atomic(dest, data)
                    blocks.append({"type": "text", "text": f"[Bild gespeichert: {dest}]"})
            return blocks

    if ext in TEXT_EXTENSIONS:
        data = await _read_limited(file, MAX_TEXT_BYTES)
        if data is not None:
            try:
                return [{"type": "text", "text": f"[{name}]\n{data.decode('utf-8')}"}]
            except UnicodeDecodeError:
                pass

    if workspace is not None:
        dest = _safe_dest(workspace, name)
        if dest is None:
            return [{"type": "text", "text": "[Anhang abgelehnt: ungültiger Dateiname]"}]
        await _stream_atomic(file, dest)
        return [{"type": "text", "text": f"[Datei hochgeladen: {dest}]"}]

    return [{"type": "text", "text": f"[Anhang: {name} — kein Workspace verfügbar]"}]


async def _read_limited(file: UploadFile, limit: int) -> bytes | None:
    """Liest höchstens limit+1 Bytes und setzt den Stream danach zurück."""
    await file.seek(0)
    data = await file.read(limit + 1)
    await file.seek(0)
    return data if len(data) <= limit else None


async def _stream_atomic(file: UploadFile, dest: Path) -> None:
    """Schreibt einen Upload begrenzt und atomar, ohne den Event-Loop zu blockieren."""
    temp = dest.with_name(f".{dest.name}.upload-{uuid4().hex}")
    written = 0
    try:
        await file.seek(0)
        async with await anyio.open_file(temp, "xb") as target:
            while chunk := await file.read(STREAM_CHUNK_BYTES):
                written += len(chunk)
                if written > MAX_FILE_BYTES:
                    raise UploadTooLarge("file", MAX_FILE_BYTES, written, dest.name)
                await target.write(chunk)
        await anyio.to_thread.run_sync(os.replace, temp, dest)
    finally:
        await anyio.to_thread.run_sync(temp.unlink, True)


async def _write_small_atomic(dest: Path, data: bytes) -> None:
    temp = dest.with_name(f".{dest.name}.upload-{uuid4().hex}")
    try:
        async with await anyio.open_file(temp, "xb") as target:
            await target.write(data)
        await anyio.to_thread.run_sync(os.replace, temp, dest)
    finally:
        await anyio.to_thread.run_sync(temp.unlink, True)


def _safe_dest(workspace: Path, name: str) -> Path | None:
    """Akzeptiert nur Basis-Dateinamen und erzeugt kollisionsfreie Ziele."""
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        return None
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        dest = safe_path(workspace, name)
    except (OSError, PathOutsideWorkspace):
        return None
    if dest == workspace.resolve():
        return None
    if not dest.exists():
        return dest
    for number in range(2, 10_000):
        candidate = dest.with_name(f"{dest.stem}-{number}{dest.suffix}")
        if not candidate.exists():
            return candidate
    return None
