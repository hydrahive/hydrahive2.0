"""Begrenzte lokale PDF-Textextraktion mit Poppler und Tesseract."""
from __future__ import annotations

import re
import time
from pathlib import Path

from hydrahive.tools import _document_process

MAX_OUTPUT_CHARS = 100_000
_TOTAL_TIMEOUT = 300
_INFO_TIMEOUT = 15
_TEXT_TIMEOUT = 45
_RENDER_TIMEOUT = 30
_OCR_TIMEOUT = 45
_MIN_TEXT_CHARS = 20


class DocumentReadError(RuntimeError):
    """Begrenzter, für Tool-Nutzer geeigneter Fehler ohne Dokumentinhalt."""


def _run(argv: list[str], timeout: float, root: Path, work: Path, max_bytes: int) -> str:
    try:
        return _document_process.run(argv, timeout, root, work, max_bytes)
    except _document_process.DocumentIsolationError as exc:
        raise DocumentReadError(str(exc)) from exc


def _remaining(deadline: float, maximum: int) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DocumentReadError("Zeitlimit für lokale PDF-Verarbeitung überschritten.")
    return min(float(maximum), remaining)


def _page_count(path: Path, deadline: float, work: Path) -> int:
    try:
        output = _run(["pdfinfo", str(path)], _remaining(deadline, _INFO_TIMEOUT), path.parent, work, 262_144)
    except _document_process.ProcessFailed as exc:
        raise DocumentReadError("PDF konnte nicht gelesen werden (beschädigt oder verschlüsselt).") from exc
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise DocumentReadError("PDF-Seitenzahl konnte nicht bestimmt werden.")
    return int(match.group(1))


def _text_pages(path: Path, start: int, end: int, deadline: float, work: Path) -> list[str]:
    argv = ["pdftotext", "-f", str(start), "-l", str(end), "-layout", str(path), "-"]
    try:
        output = _run(argv, _remaining(deadline, _TEXT_TIMEOUT), path.parent, work, 2_000_000)
    except _document_process.ProcessFailed as exc:
        raise DocumentReadError("PDF-Text konnte lokal nicht gelesen werden.") from exc
    pages = output.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    expected = end - start + 1
    return [page.strip() for page in (pages + [""] * expected)[:expected]]


def _has_text(text: str) -> bool:
    return sum(character.isalnum() for character in text) >= _MIN_TEXT_CHARS


def _ocr_page(path: Path, page: int, language: str, work: Path, deadline: float) -> str:
    prefix = work / f"page-{page}"
    image = Path(str(prefix) + ".png")
    render = [
        "pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
        "-scale-to", "2500", "-png", str(path), str(prefix),
    ]
    try:
        _run(render, _remaining(deadline, _RENDER_TIMEOUT), path.parent, work, 65_536)
        return _run(
            ["tesseract", str(image), "stdout", "-l", language],
            _remaining(deadline, _OCR_TIMEOUT), path.parent, work, 1_000_000,
        ).strip()
    except _document_process.ProcessFailed as exc:
        raise DocumentReadError(f"OCR für Seite {page} ist lokal fehlgeschlagen.") from exc
    finally:
        image.unlink(missing_ok=True)


def _format_pages(start: int, pages: list[str]) -> str:
    return "\n\n".join(
        f"[Seite {start + offset}]\n{text or '(kein Text erkannt)'}" for offset, text in enumerate(pages)
    )


def extract_document(
    path: Path,
    *,
    page_start: int,
    page_limit: int,
    ocr_language: str,
    force_ocr: bool,
) -> dict:
    """Extrahiert den gewählten Seitenbereich lokal und liefert Text plus Zähler."""
    work = path.parent / "work"
    work.mkdir(mode=0o700, exist_ok=True)
    deadline = time.monotonic() + _TOTAL_TIMEOUT
    total_pages = _page_count(path, deadline, work)
    if page_start > total_pages:
        raise DocumentReadError(f"page_start liegt hinter dem Dokumentende ({total_pages} Seiten).")
    page_end = min(total_pages, page_start + page_limit - 1)
    pages = [""] * (page_end - page_start + 1) if force_ocr else _text_pages(path, page_start, page_end, deadline, work)
    text_pages = 0
    ocr_pages = 0
    for offset, text in enumerate(pages):
        if force_ocr or not _has_text(text):
            pages[offset] = _ocr_page(path, page_start + offset, ocr_language, work, deadline)
            ocr_pages += 1
        else:
            text_pages += 1
    output = _format_pages(page_start, pages)
    output_truncated = len(output) > MAX_OUTPUT_CHARS
    if output_truncated:
        output = output[:MAX_OUTPUT_CHARS]
    next_page = page_end + 1 if page_end < total_pages else None
    return {
        "text": output,
        "total_pages": total_pages,
        "returned_pages": len(pages),
        "text_pages": text_pages,
        "ocr_pages": ocr_pages,
        "next_page": next_page,
        "truncated": output_truncated or next_page is not None,
    }
