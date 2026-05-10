"""Import-Job: qcow2-Source wird 1:1 kopiert (kein qemu-img convert).

Hintergrund: qemu-img convert ändert cluster_size + subformat. FreeBSDs
gptzfsboot ist gegen Layout-Wechsel empfindlich und liefert "ZFS I/O
error" / "no bootable disks" beim Boot wenn die Original-qcow2 ein
anderes Layout hatte als qemu-img-Default.

Frische Installation in HH2 funktioniert (gleiche Args), nur der Import-
Pfad bricht das Image — Beweis dass run_convert das Image strukturell
verändert auch wenn es schon qcow2 ist.

Tests: nach execute_job() mit qcow2-Source ist dst BIT-FÜR-BIT identisch
zur src (sha256 match). Plus: bei nicht-qcow2 wird convert noch gerufen.
"""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def qcow2_factory(tmp_path):
    """Erzeugt eine kleine echte qcow2 via qemu-img create. Skip wenn nicht da."""
    def _make(name: str, size: str = "10M") -> Path:
        target = tmp_path / name
        try:
            import subprocess
            r = subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", str(target), size],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode != 0:
                pytest.skip(f"qemu-img create fehlgeschlagen: {r.stderr}")
        except FileNotFoundError:
            pytest.skip("qemu-img nicht installiert — Test wird übersprungen")
        return target
    return _make


def test_qcow2_source_is_copied_byte_for_byte(tmp_path, qcow2_factory, monkeypatch):
    """Bei fmt=qcow2 wird shutil.copy2 statt qemu-img convert verwendet."""
    from hydrahive.vms import import_job as ij

    src = qcow2_factory("source.qcow2", "10M")
    dst = tmp_path / "imported.qcow2"
    src_hash = _sha256(src)

    # detect_format mockt 'qcow2'
    async def _fake_detect(path):
        return "qcow2"
    monkeypatch.setattr(ij, "detect_format", _fake_detect)

    # run_convert SOLL NICHT gerufen werden — wir tracken das
    convert_called = {"n": 0}
    async def _fake_convert(src, dst, fmt, jid):
        convert_called["n"] += 1
    monkeypatch.setattr(ij, "run_convert", _fake_convert)

    # DB-Helper mocken — keine echte DB nötig für diesen Test
    monkeypatch.setattr(ij, "db_get", lambda jid: {
        "source_path": str(src), "target_qcow2": str(dst),
    })
    monkeypatch.setattr(ij, "db_update", lambda *a, **kw: None)

    asyncio.run(ij.execute_job("test-job", cleanup_source=False))

    assert dst.exists(), "Ziel-File wurde nicht angelegt"
    assert convert_called["n"] == 0, "qemu-img convert wurde gerufen — sollte nicht"
    assert _sha256(dst) == src_hash, "Bit-für-bit-Identität verletzt"


def test_non_qcow2_source_uses_convert(tmp_path, monkeypatch):
    """Bei fmt=raw/vmdk/etc. wird run_convert weiter gerufen."""
    from hydrahive.vms import import_job as ij

    src = tmp_path / "source.raw"
    src.write_bytes(b"\x00" * 1024)
    dst = tmp_path / "imported.qcow2"

    async def _fake_detect(path):
        return "raw"
    monkeypatch.setattr(ij, "detect_format", _fake_detect)

    convert_called = {"args": None}
    async def _fake_convert(s, d, fmt, jid):
        convert_called["args"] = (s, d, fmt, jid)
        # Simuliere Erfolg — schreib leere Datei
        Path(d).write_bytes(b"")
    monkeypatch.setattr(ij, "run_convert", _fake_convert)

    monkeypatch.setattr(ij, "db_get", lambda jid: {
        "source_path": str(src), "target_qcow2": str(dst),
    })
    monkeypatch.setattr(ij, "db_update", lambda *a, **kw: None)

    asyncio.run(ij.execute_job("test-job-2", cleanup_source=False))

    assert convert_called["args"] is not None, "run_convert wurde nicht gerufen"
    assert convert_called["args"][2] == "raw"
