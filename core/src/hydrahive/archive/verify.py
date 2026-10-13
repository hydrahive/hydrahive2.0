"""Schritt 5 „Prüfen“ (Spec archiv-system.md, Etappe 2): Paket ganz neu lesen.

sha256 gleich der .json, gzip fehlerfrei bis zum Ende, Zahl der Einträge stimmt.
Erst danach darf gelöscht werden.
"""
from __future__ import annotations

import hashlib
import json
import tarfile
import zlib
from pathlib import Path

_CHUNK = 1024 * 1024


class VerifyError(Exception):
    pass


def verify(tgz: Path) -> None:
    meta_path = tgz.with_name(tgz.name + ".json")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise VerifyError(f"Begleitdatei unlesbar: {e}") from e
    sha = hashlib.sha256()
    with open(tgz, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            sha.update(chunk)
    if sha.hexdigest() != meta.get("sha256"):
        raise VerifyError("Prüfsumme stimmt nicht")
    count = 0
    try:
        with tarfile.open(tgz, mode="r:gz") as tar:
            for member in tar:
                count += 1
                if member.isreg():
                    f = tar.extractfile(member)
                    if f is not None:
                        while f.read(_CHUNK):
                            pass
    except (tarfile.TarError, OSError, EOFError, zlib.error) as e:
        raise VerifyError(f"Paket nicht lesbar: {e}") from e
    if "entries" in meta and count != meta["entries"]:
        raise VerifyError(f"{count} Einträge statt {meta['entries']}")
