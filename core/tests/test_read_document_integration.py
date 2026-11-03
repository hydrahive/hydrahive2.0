"""Echte lokale Poppler-/Tesseract-Proben; ohne Laufzeitprogramme sauber übersprungen."""
from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from hydrahive.tools import _document_process
from hydrahive.tools._document_local import extract_document

_REQUIRED = ["pdfinfo", "pdftotext", "pdftoppm", "tesseract"]
_REQUIRED += ["bwrap", "prlimit"] if platform.system() == "Linux" else ["sandbox-exec"]
_TOOLS_READY = all(shutil.which(name) for name in _REQUIRED)
if _TOOLS_READY:
    _TOOLS_READY = "eng" in subprocess.run(
        ["tesseract", "--list-langs"], capture_output=True, text=True, check=False,
    ).stdout.splitlines()
pytestmark = pytest.mark.skipif(not _TOOLS_READY, reason="Poppler/Tesseract mit eng nicht installiert")


@pytest.fixture
def sandbox_tmp() -> Path:
    with tempfile.TemporaryDirectory(prefix="hydrahive-document-", dir="/tmp") as temp:
        yield Path(temp)


def _text_pdf(path: Path, texts: list[str]) -> None:
    """Kleine echte PDF mit Helvetica-Text und korrekter xref-Tabelle."""
    count = len(texts)
    page_ids = list(range(3, 3 + count))
    content_ids = list(range(3 + count, 3 + 2 * count))
    font_id = 3 + 2 * count
    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in page_ids)}] /Count {count} >>",
    ]
    for content_id in content_ids:
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
    for text in texts:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 18 Tf 72 720 Td ({escaped}) Tj ET"
        objects.append(f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n{body}\nendobj\n".encode())
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)


def _scan_pdf(path: Path, text: str) -> None:
    image = Image.new("RGB", (1800, 450), "white")
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    font = ImageFont.truetype(str(font_path), 72) if font_path.exists() else ImageFont.load_default(size=60)
    ImageDraw.Draw(image).text((80, 150), text, fill="black", font=font)
    image.save(path, "PDF", resolution=150.0)


def test_real_text_pdf_has_exact_pages_and_continuation(sandbox_tmp: Path) -> None:
    pdf = sandbox_tmp / "input.pdf"
    _text_pdf(pdf, [
        "TEXT DOCUMENT PAGE ONE NUMBER 11111",
        "TEXT DOCUMENT PAGE TWO NUMBER 22222",
        "TEXT DOCUMENT PAGE THREE NUMBER 33333",
    ])

    result = extract_document(pdf, page_start=1, page_limit=2, ocr_language="eng", force_ocr=False)

    assert result["total_pages"] == 3
    assert result["returned_pages"] == 2
    assert result["text_pages"] == 2
    assert result["ocr_pages"] == 0
    assert result["next_page"] == 3
    assert "[Seite 1]\nTEXT DOCUMENT PAGE ONE NUMBER 11111" in result["text"]
    assert "[Seite 2]\nTEXT DOCUMENT PAGE TWO NUMBER 22222" in result["text"]


def test_real_scan_pdf_is_read_locally_by_ocr(sandbox_tmp: Path) -> None:
    pdf = sandbox_tmp / "input.pdf"
    _scan_pdf(pdf, "HYDRAHIVE OCR TEST 4711")

    result = extract_document(pdf, page_start=1, page_limit=1, ocr_language="eng", force_ocr=False)

    assert result["text_pages"] == 0
    assert result["ocr_pages"] == 1
    assert "HYDRAHIVE" in result["text"].upper()
    assert "4711" in result["text"]


@pytest.mark.skipif(platform.system() != "Linux", reason="Linux-Netzwerk-Namespace")
def test_linux_sandbox_has_no_network(sandbox_tmp: Path) -> None:
    work = sandbox_tmp / "work"
    work.mkdir()
    code = "import socket; socket.create_connection(('1.1.1.1', 53), 1)"
    with pytest.raises(_document_process.ProcessFailed):
        _document_process.run(["python3", "-c", code], 5, sandbox_tmp, work, 1024)


def test_sandbox_cannot_read_another_document_snapshot(sandbox_tmp: Path) -> None:
    work = sandbox_tmp / "work"
    work.mkdir()
    with tempfile.TemporaryDirectory(prefix="hydrahive-document-other-", dir="/tmp") as other:
        secret = Path(other) / "input.pdf"
        secret.write_text("FREMDES DOKUMENT", encoding="utf-8")
        with pytest.raises(_document_process.ProcessFailed):
            _document_process.run(["cat", str(secret)], 5, sandbox_tmp, work, 1024)


@pytest.mark.skipif(not shutil.which("pdfunite"), reason="pdfunite nicht installiert")
def test_real_mixed_pdf_keeps_page_assignment(sandbox_tmp: Path) -> None:
    text_pdf = sandbox_tmp / "text.pdf"
    scan_pdf = sandbox_tmp / "scan.pdf"
    mixed = sandbox_tmp / "input.pdf"
    _text_pdf(text_pdf, ["EMBEDDED TEXT PAGE 12345"])
    _scan_pdf(scan_pdf, "SCANNED PAGE 67890")
    subprocess.run(["pdfunite", str(text_pdf), str(scan_pdf), str(mixed)], check=True)

    result = extract_document(mixed, page_start=1, page_limit=2, ocr_language="eng", force_ocr=False)

    assert (result["total_pages"], result["text_pages"], result["ocr_pages"]) == (2, 1, 1)
    assert result["next_page"] is None
    first, second = result["text"].split("[Seite 2]")
    assert "EMBEDDED TEXT" in first
    assert "SCANNED PAGE" in second.upper()
