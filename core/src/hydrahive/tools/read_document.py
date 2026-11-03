"""Sicheres Tool zum lokalen Lesen von Text- und Scan-PDFs."""
from __future__ import annotations

import asyncio
import fcntl
import os
import platform
import re
import stat
import tempfile
import threading
from pathlib import Path

from hydrahive.tools import _document_local, _fs
from hydrahive.tools._path import PathOutsideWorkspace, read_path
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_MAX_FILE_BYTES = 100 * 1024 * 1024
_LANGUAGE = re.compile(r"[A-Za-z0-9_-]+(?:\+[A-Za-z0-9_-]+)*\Z")
_PARSER_SLOTS = threading.BoundedSemaphore(2)
_DESCRIPTION = (
    "Liest eine PDF ausschließlich lokal in einer isolierten Parser-Sandbox. Vorhandener Text wird mit Poppler "
    "extrahiert; Scan-Seiten werden bei Bedarf lokal mit Tesseract erkannt. Nutze dies für PDFs statt file_read."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "PDF-Pfad relativ zum Workspace oder zulässiger Lesepfad."},
        "page_start": {"type": "integer", "minimum": 1, "default": 1, "description": "Erste Seite (1-basiert)."},
        "page_limit": {
            "type": "integer", "minimum": 1, "maximum": 20, "default": 10,
            "description": "Maximal zu lesende Seiten (höchstens 20).",
        },
        "ocr_language": {
            "type": "string", "default": "deu+eng", "maxLength": 64,
            "pattern": r"^[A-Za-z0-9_-]+(?:\+[A-Za-z0-9_-]+)*$",
            "description": "Installierte Tesseract-Sprachen, z. B. deu+eng.",
        },
        "force_ocr": {"type": "boolean", "default": False, "description": "Alle gewählten Seiten per OCR lesen."},
    },
    "required": ["path"],
    "additionalProperties": False,
}


def _integer(args: dict, name: str, default: int, maximum: int | None = None) -> int:
    value = args.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} muss eine positive Ganzzahl sein.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} darf höchstens {maximum} sein.")
    return value


def _arguments(args: dict) -> tuple[str, int, int, str, bool]:
    path = args.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("path muss ein nicht-leerer PDF-Pfad sein.")
    start = _integer(args, "page_start", 1)
    limit = _integer(args, "page_limit", 10, 20)
    language = args.get("ocr_language", "deu+eng")
    if not isinstance(language, str) or len(language) > 64 or not _LANGUAGE.fullmatch(language):
        raise ValueError("ocr_language ist ungültig (maximal 64 Zeichen: Buchstaben, Ziffern, _, -, +).")
    force_ocr = args.get("force_ocr", False)
    if not isinstance(force_ocr, bool):
        raise ValueError("force_ocr muss true oder false sein.")
    return path, start, limit, language, force_ocr


def _opened_path(fd: int) -> Path:
    """Tatsächlich geöffnetes Ziel, damit Autorisierung und Dateideskriptor identisch bleiben."""
    system = platform.system()
    if system == "Linux":
        return Path(os.readlink(f"/proc/self/fd/{fd}")).resolve()
    if system == "Darwin":
        raw = fcntl.fcntl(fd, 50, b"\0" * 1024)  # F_GETPATH aus <fcntl.h>
        value = bytes(raw).split(b"\0", 1)[0].decode("utf-8", errors="strict")
        return Path(value).resolve()
    raise ValueError("Symlink-sicheres Dokumentlesen ist auf diesem Betriebssystem nicht verfügbar.")


def _snapshot_pdf(ctx: ToolContext, requested: str, folder: Path) -> tuple[Path, Path]:
    if Path(requested).suffix.lower() != ".pdf":
        raise ValueError("Nur Dateien mit der Endung .pdf werden unterstützt.")
    source_path = read_path(ctx, requested)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(source_path, flags)
    except FileNotFoundError as exc:
        raise ValueError(f"Datei nicht gefunden: {requested}") from exc
    except OSError as exc:
        raise ValueError("PDF-Datei konnte nicht symlink-sicher geöffnet werden.") from exc
    snapshot = folder / "input.pdf"
    try:
        before = os.fstat(fd)
        if _opened_path(fd) != source_path:
            raise ValueError("Geöffnetes PDF-Ziel liegt nicht mehr am autorisierten Pfad.")
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Der PDF-Pfad muss eine reguläre Datei sein.")
        if before.st_size > _MAX_FILE_BYTES:
            raise ValueError("PDF-Datei ist größer als 100 MiB.")
        copied = 0
        with os.fdopen(fd, "rb", closefd=False) as source, snapshot.open("xb") as target:
            header = source.read(5)
            if header != b"%PDF-":
                raise ValueError("Datei hat keine gültige PDF-Kennung.")
            target.write(header)
            copied = 5
            while chunk := source.read(1024 * 1024):
                copied += len(chunk)
                if copied > _MAX_FILE_BYTES:
                    raise ValueError("PDF-Datei ist größer als 100 MiB.")
                target.write(chunk)
        after = os.fstat(fd)
        stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        if stable != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or copied != after.st_size:
            raise ValueError("PDF-Datei wurde während des Lesens verändert; bitte erneut versuchen.")
        snapshot.chmod(0o400)
        return source_path, snapshot
    except OSError as exc:
        raise ValueError("PDF-Datei konnte nicht sicher kopiert werden.") from exc
    finally:
        os.close(fd)


def _read_local(ctx: ToolContext, requested: str, start: int, limit: int, language: str, force_ocr: bool):
    if not _PARSER_SLOTS.acquire(timeout=5):
        raise _document_local.DocumentReadError("Zu viele Dokumente werden gleichzeitig verarbeitet; bitte erneut versuchen.")
    try:
        temp_root = "/tmp" if platform.system() == "Linux" else None  # AppArmor-Profil ist auf diesen Privatpfad eng.
        with tempfile.TemporaryDirectory(prefix="hydrahive-document-", dir=temp_root) as temp:
            shown, snapshot = _snapshot_pdf(ctx, requested, Path(temp))
            result = _document_local.extract_document(
                snapshot, page_start=start, page_limit=limit, ocr_language=language, force_ocr=force_ocr,
            )
            return shown, result
    finally:
        _PARSER_SLOTS.release()


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        requested, start, limit, language, force_ocr = _arguments(args)
        try:
            execution = _fs._execution(ctx)
        except _fs.ExecutionUnavailable as exc:
            return ToolResult.fail(f"{exc.code}: Dokument-Ausführungsort ist nicht verfügbar.")
        if execution["mode"] == "container":
            return ToolResult.fail("read_document ist für Container-Projekte nicht verfügbar.")
        shown, result = await asyncio.to_thread(_read_local, ctx, requested, start, limit, language, force_ocr)
    except (ValueError, PathOutsideWorkspace, _document_local.DocumentReadError) as exc:
        return ToolResult.fail(str(exc))
    text = result.pop("text")
    return ToolResult.ok(text, path=str(shown), **result)


TOOL = Tool(name="read_document", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="files")
