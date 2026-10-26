"""mutagen ist Kern-Abhängigkeit (Till 26.10.2026: „fest in hydra“).

Module wie radiostream (Musik-Bibliothek, hydrahive2-modules radiostream/SPEC.md) lesen damit Künstler, Titel, Album,
Länge … aus MP3/FLAC. Module bringen keine eigenen Python-Pakete mit – deshalb im Kern, damit jedes Update es pflegt.
"""
from __future__ import annotations

import re
import struct
from io import BytesIO
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_mutagen_steht_mit_deckel_in_den_abhaengigkeiten() -> None:
    text = PYPROJECT.read_text()
    assert re.search(r'^\s*"mutagen>=1\.47,<2",', text, re.M), "mutagen fehlt oder ohne Versionsdeckel"


def _minimal_flac(seconds: int = 3, rate: int = 44100) -> bytes:
    """Kleinstes gültiges FLAC: Marke + STREAMINFO (keine Audio-Frames nötig für die Kopfdaten)."""
    total = seconds * rate
    info = struct.pack(">HH", 4096, 4096) + b"\x00\x00\x00" + b"\x00\x00\x00"
    # 20 Bit Rate, 3 Bit Kanäle-1, 5 Bit Bits-1, 36 Bit Samples
    packed = (rate << 44) | (1 << 41) | (15 << 36) | total
    info += packed.to_bytes(8, "big") + b"\x00" * 16
    header = bytes([0x80]) + len(info).to_bytes(3, "big")      # letzter Block, Typ 0 = STREAMINFO
    return b"fLaC" + header + info


def test_mutagen_liest_flac_kopfdaten_aus_einem_stream() -> None:
    """Wie im Modul: aus einem geöffneten Datei-Objekt (SMB), nicht aus einem Pfad."""
    import mutagen
    from mutagen.flac import FLAC

    f = FLAC(BytesIO(_minimal_flac()))
    f["artist"] = "Testkünstler"
    out = BytesIO(_minimal_flac())
    f.save(out)
    out.seek(0)
    m = mutagen.File(out, easy=True)
    assert m is not None
    assert m["artist"] == ["Testkünstler"]
    assert round(m.info.length) == 3
