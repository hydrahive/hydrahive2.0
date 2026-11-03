from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def document_modules():
    return (
        importlib.import_module("hydrahive.tools.read_document"),
        importlib.import_module("hydrahive.tools._document_local"),
    )


def _ctx(workspace: Path) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=workspace)


def _pdf(path: Path, body: bytes = b"text") -> Path:
    path.write_bytes(b"%PDF-1.7\n" + body)
    return path


def _execute(module, args: dict, workspace: Path):
    return asyncio.run(module._execute(args, _ctx(workspace)))


def test_schema_beschreibt_vertrag(document_modules):
    read_document, _ = document_modules
    schema = read_document.TOOL.schema
    assert schema["required"] == ["path"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["page_start"]["minimum"] == 1
    assert schema["properties"]["page_limit"]["maximum"] == 20
    assert schema["properties"]["ocr_language"]["default"] == "deu+eng"
    assert schema["properties"]["force_ocr"]["default"] is False


def test_gueltige_pdf_liefert_text_und_metadaten(document_modules, tmp_path, monkeypatch):
    read_document, local = document_modules
    pdf = _pdf(tmp_path / "scan.pdf")
    monkeypatch.setattr(local, "extract_document", lambda *a, **kw: {
        "text": "[Seite 1]\nHallo",
        "total_pages": 1,
        "returned_pages": 1,
        "text_pages": 1,
        "ocr_pages": 0,
        "next_page": None,
        "truncated": False,
    })

    result = _execute(read_document, {"path": pdf.name}, tmp_path)

    assert result.success is True
    assert result.output == "[Seite 1]\nHallo"
    assert result.metadata == {
        "path": str(pdf),
        "total_pages": 1,
        "returned_pages": 1,
        "text_pages": 1,
        "ocr_pages": 0,
        "next_page": None,
        "truncated": False,
    }


def test_parser_erhaelt_nur_privaten_snapshot_des_geprueften_dateideskriptors(document_modules, tmp_path, monkeypatch):
    read_document, local = document_modules
    original = _pdf(tmp_path / "original.pdf", b"stabiler Inhalt")
    captured = {}

    def inspect_snapshot(path, **kwargs):
        captured.update(path=path, body=path.read_bytes(), mode=path.stat().st_mode & 0o777)
        return {"text": "ok", "total_pages": 1, "returned_pages": 1, "text_pages": 1,
                "ocr_pages": 0, "next_page": None, "truncated": False}

    monkeypatch.setattr(local, "extract_document", inspect_snapshot)
    result = _execute(read_document, {"path": original.name}, tmp_path)

    assert result.success is True
    assert captured["path"] != original
    assert captured["body"] == original.read_bytes()
    assert captured["mode"] == 0o400
    assert not captured["path"].exists()
    assert result.metadata["path"] == str(original)


def test_geoeffnetes_ziel_wird_nach_open_erneut_autorisiert(document_modules, tmp_path, monkeypatch):
    read_document, local = document_modules
    _pdf(tmp_path / "race.pdf")
    monkeypatch.setattr(read_document, "_opened_path", lambda _fd: tmp_path.parent / "fremd.pdf")
    monkeypatch.setattr(local, "extract_document", lambda *a, **kw: pytest.fail("Parser darf nicht starten"))

    result = _execute(read_document, {"path": "race.pdf"}, tmp_path)

    assert result.success is False
    assert "autorisierten Pfad" in (result.error or "")


@pytest.mark.parametrize("requested", ["../secret.pdf", "/etc/passwd.pdf"])
def test_pfad_ausserhalb_workspace_wird_abgelehnt(document_modules, tmp_path, requested):
    read_document, _ = document_modules
    result = _execute(read_document, {"path": requested}, tmp_path)
    assert result.success is False
    assert "außerhalb" in (result.error or "")


def test_symlink_ausbruch_wird_abgelehnt(document_modules, tmp_path):
    read_document, _ = document_modules
    outside = _pdf(tmp_path.parent / "outside.pdf")
    (tmp_path / "link.pdf").symlink_to(outside)
    result = _execute(read_document, {"path": "link.pdf"}, tmp_path)
    assert result.success is False
    assert "außerhalb" in (result.error or "")


def test_container_ausfuehrung_faellt_nie_auf_host_zurueck(document_modules, tmp_path, monkeypatch):
    read_document, local = document_modules
    _pdf(tmp_path / "container.pdf")
    monkeypatch.setattr(read_document._fs, "_execution", lambda _ctx: {"mode": "container"})
    monkeypatch.setattr(local, "extract_document", lambda *a, **kw: pytest.fail("Host-Zugriff"))

    result = _execute(read_document, {"path": "container.pdf"}, tmp_path)

    assert result.success is False
    assert "Container-Projekte" in (result.error or "")


@pytest.mark.parametrize(
    ("name", "body", "error"),
    [
        ("note.txt", b"%PDF-1.7\ntext", ".pdf"),
        ("fake.pdf", b"kein pdf", "PDF-Kennung"),
    ],
)
def test_nicht_pdf_wird_abgelehnt(document_modules, tmp_path, name, body, error):
    read_document, _ = document_modules
    (tmp_path / name).write_bytes(body)
    result = _execute(read_document, {"path": name}, tmp_path)
    assert result.success is False
    assert error in (result.error or "")


def test_verzeichnis_wird_abgelehnt(document_modules, tmp_path):
    read_document, _ = document_modules
    folder = tmp_path / "folder.pdf"
    folder.mkdir()
    result = _execute(read_document, {"path": folder.name}, tmp_path)
    assert result.success is False
    assert "reguläre Datei" in (result.error or "")


def test_dateigroesse_ist_begrenzt(document_modules, tmp_path):
    read_document, _ = document_modules
    pdf = _pdf(tmp_path / "huge.pdf")
    with pdf.open("r+b") as handle:
        handle.truncate(100 * 1024 * 1024 + 1)
    result = _execute(read_document, {"path": pdf.name}, tmp_path)
    assert result.success is False
    assert "100 MiB" in (result.error or "")


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ({"page_start": 0}, "page_start"),
        ({"page_start": True}, "page_start"),
        ({"page_limit": 0}, "page_limit"),
        ({"page_limit": 21}, "page_limit"),
        ({"page_limit": "2"}, "page_limit"),
        ({"force_ocr": "yes"}, "force_ocr"),
    ],
)
def test_seitenparameter_und_force_ocr_werden_validiert(document_modules, tmp_path, args, error):
    read_document, _ = document_modules
    pdf = _pdf(tmp_path / "ok.pdf")
    result = _execute(read_document, {"path": pdf.name, **args}, tmp_path)
    assert result.success is False
    assert error in (result.error or "")


@pytest.mark.parametrize("language", ["", "+deu", "deu+", "deu eng", "../../deu", "a" * 65])
def test_ocr_sprache_wird_begrenzt(document_modules, tmp_path, language):
    read_document, _ = document_modules
    pdf = _pdf(tmp_path / "ok.pdf")
    result = _execute(read_document, {"path": pdf.name, "ocr_language": language}, tmp_path)
    assert result.success is False
    assert "ocr_language" in (result.error or "")


def test_text_pdf_nutzt_pdfinfo_und_pdftotext_als_argv(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    pdf = _pdf(tmp_path / "name; echo PWNED.pdf")
    calls: list[list[str]] = []

    def fake_run(argv, timeout, *args, **kwargs):
        calls.append(argv)
        if argv[0] == "pdfinfo":
            return "Pages:          2\n"
        return "Erste Textseite mit mindestens zwanzig Zeichen.\fZweite Textseite ebenfalls gut lesbar.\f"

    monkeypatch.setattr(local, "_run", fake_run)
    result = local.extract_document(pdf, page_start=1, page_limit=10, ocr_language="deu+eng", force_ocr=False)

    assert calls == [
        ["pdfinfo", str(pdf)],
        ["pdftotext", "-f", "1", "-l", "2", "-layout", str(pdf), "-"],
    ]
    assert result["text_pages"] == 2
    assert result["ocr_pages"] == 0
    assert "[Seite 1]" in result["text"] and "[Seite 2]" in result["text"]


def test_gemischte_pdf_ocr_nur_fuer_kurze_seite(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    pdf = _pdf(tmp_path / "mixed.pdf")
    calls: list[list[str]] = []

    def fake_run(argv, timeout, *args, **kwargs):
        calls.append(argv)
        if argv[0] == "pdfinfo":
            return "Pages: 3\n"
        if argv[0] == "pdftotext":
            return "Genug eingebetteter Text auf Seite eins.\fx\fAuch Seite drei hat ausreichend Text.\f"
        if argv[0] == "tesseract":
            return "Lokaler OCR Text der zweiten Seite"
        return ""

    monkeypatch.setattr(local, "_run", fake_run)
    result = local.extract_document(pdf, page_start=1, page_limit=3, ocr_language="deu+eng", force_ocr=False)

    render = next(call for call in calls if call[0] == "pdftoppm")
    ocr = next(call for call in calls if call[0] == "tesseract")
    assert render[1:7] == ["-f", "2", "-l", "2", "-singlefile", "-scale-to"]
    assert "2500" in render
    assert ocr[-2:] == ["-l", "deu+eng"]
    assert result["text_pages"] == 2
    assert result["ocr_pages"] == 1
    assert "Lokaler OCR Text" in result["text"]


def test_force_ocr_erkennt_jede_gewaehlte_seite(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    pdf = _pdf(tmp_path / "force.pdf")
    rendered: list[int] = []

    def fake_run(argv, timeout, *args, **kwargs):
        if argv[0] == "pdfinfo":
            return "Pages: 2\n"
        if argv[0] == "pdftotext":
            return "Lesbarer Text auf der ersten Seite.\fLesbarer Text auf der zweiten Seite.\f"
        if argv[0] == "pdftoppm":
            rendered.append(int(argv[2]))
            return ""
        return f"OCR Seite {rendered[-1]}"

    monkeypatch.setattr(local, "_run", fake_run)
    result = local.extract_document(pdf, page_start=1, page_limit=2, ocr_language="eng", force_ocr=True)
    assert rendered == [1, 2]
    assert result["text_pages"] == 0
    assert result["ocr_pages"] == 2


def test_seitenbereich_setzt_fortsetzung(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    pdf = _pdf(tmp_path / "many.pdf")

    def fake_run(argv, timeout, *args, **kwargs):
        if argv[0] == "pdfinfo":
            return "Pages: 9\n"
        return "Seite mit ausreichend alphanumerischem Inhalt.\f" * 3

    monkeypatch.setattr(local, "_run", fake_run)
    result = local.extract_document(pdf, page_start=4, page_limit=3, ocr_language="eng", force_ocr=False)
    assert result["returned_pages"] == 3
    assert result["next_page"] == 7
    assert result["truncated"] is True
    assert result["text"].startswith("[Seite 4]")


def test_ausgabe_ist_auf_100000_zeichen_begrenzt(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    pdf = _pdf(tmp_path / "long.pdf")

    def fake_run(argv, timeout, *args, **kwargs):
        if argv[0] == "pdfinfo":
            return "Pages: 1\n"
        return "a" * 120_000 + "\f"

    monkeypatch.setattr(local, "_run", fake_run)
    result = local.extract_document(pdf, page_start=1, page_limit=1, ocr_language="eng", force_ocr=False)
    assert len(result["text"]) <= 100_000
    assert result["truncated"] is True


def test_fehlende_isolation_hat_installationshinweis(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    monkeypatch.setattr(
        local._document_process, "run",
        lambda *a, **kw: (_ for _ in ()).throw(local._document_process.DocumentIsolationError("Isolation fehlt")),
    )
    with pytest.raises(local.DocumentReadError, match="Isolation fehlt"):
        local._run(["pdfinfo", "doc.pdf"], 1, tmp_path, tmp_path, 1000)


def test_beschaedigte_oder_verschluesselte_pdf_leakt_keinen_stderr(document_modules, tmp_path, monkeypatch):
    _, local = document_modules
    pdf = _pdf(tmp_path / "broken.pdf")
    monkeypatch.setattr(
        local, "_run",
        lambda *a, **kw: (_ for _ in ()).throw(local._document_process.ProcessFailed("pdfinfo")),
    )

    with pytest.raises(local.DocumentReadError) as exc:
        local.extract_document(pdf, page_start=1, page_limit=1, ocr_language="eng", force_ocr=False)

    assert "beschädigt oder verschlüsselt" in str(exc.value)
    assert "SECRET" not in str(exc.value)
