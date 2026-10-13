"""Archiv-Paket bauen: tar.gz + .json (Spec archiv-system.md, Etappe 1).

Erst `<name>.part` schreiben (Prüfsumme läuft mit), dann per os.replace auf
den Endnamen und danach die .json. Ein Paket ohne .json oder mit .part ist
also nie „fertig“ – das Löschen (Etappe 2) verlässt sich darauf.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.archive._paths import kind_dir

logger = logging.getLogger(__name__)

_SAFE = re.compile(r"[^A-Za-z0-9_-]+")


class _HashingWriter:
    """Datei-Objekt für tarfile, das beim Schreiben sha256 mitrechnet."""

    def __init__(self, fh) -> None:
        self._fh = fh
        self.sha256 = hashlib.sha256()

    def write(self, data: bytes) -> int:
        self.sha256.update(data)
        return self._fh.write(data)

    def flush(self) -> None:
        self._fh.flush()


def _safe(text: str, limit: int) -> str:
    cleaned = _SAFE.sub("-", text).strip("-_")
    return (cleaned[:limit].rstrip("-_")) or "unbenannt"


def _target(kind: str, name: str, source_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    base = f"{stamp}_{_safe(name, 40)}_{_safe(source_id, 8)}"
    folder = kind_dir(kind)
    candidate, n = folder / f"{base}.tar.gz", 1
    while candidate.exists() or candidate.with_name(candidate.name + ".part").exists():
        n += 1
        candidate = folder / f"{base}-{n}.tar.gz"
    return candidate


def _add_tree(tar: tarfile.TarFile, arcname: str, source: Path) -> None:
    """Wie tar.add(recursive=True), aber ohne eingehängte Laufwerke. Symlinks
    werden als Symlinks gesichert (nicht verfolgt).

    Bewusst NICHT backup._paths.is_excluded: Das System-Backup lässt VM-Platten
    und Ordner wie vms/ oder tls/ weg. Ein Archiv soll vollständig sein: Was
    der Nutzer hatte, kommt mit."""
    tar.add(source, arcname=arcname, recursive=False)
    if source.is_symlink() or not source.is_dir():
        return
    for root, dirs, files in os.walk(source, followlinks=False):
        here = Path(root)
        keep = []
        for d in sorted(dirs):
            p = here / d
            if os.path.ismount(p):
                logger.info("Archiv: eingehängtes Laufwerk übersprungen: %s", p)
                continue
            keep.append(d)
            tar.add(p, arcname=f"{arcname}/{p.relative_to(source)}", recursive=False)
        dirs[:] = keep
        for f in sorted(files):
            p = here / f
            tar.add(p, arcname=f"{arcname}/{p.relative_to(source)}", recursive=False)


def pack(*, kind: str, name: str, source_id: str, owner: str | None, reason: str,
         sources: list[tuple[str, Path]], extra: dict[str, Any] | None = None) -> dict:
    """Packt `sources` ([(arcname, pfad)]) ins Archiv. Gibt die .json-Daten zurück."""
    target = _target(kind, name, source_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    try:
        with open(part, "xb") as fh:
            writer = _HashingWriter(fh)
            with tarfile.open(fileobj=writer, mode="w:gz") as tar:
                for arcname, src in sources:
                    if os.path.lexists(src):
                        _add_tree(tar, _safe(arcname, 60), Path(src))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(part, target)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    meta = {
        "file": target.name, "kind": kind, "name": name, "source_id": source_id,
        "owner": owner, "reason": reason, "extra": extra or {},
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": target.stat().st_size, "sha256": writer.sha256.hexdigest(),
    }
    json_path = target.with_name(target.name + ".json")
    tmp = json_path.with_name(json_path.name + ".part")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, json_path)
    logger.info("Archiviert: %s/%s (%d Bytes, Grund %s)", kind, target.name, meta["size"], reason)
    return meta
