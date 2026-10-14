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
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.archive import location
from hydrahive.archive._paths import kind_dir
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_SAFE = re.compile(r"[^A-Za-z0-9_-]+")
_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9_.-]+")

OnFile = Callable[[int], None]   # wird je gepackter Datei mit ihrer Größe aufgerufen
OnTarget = Callable[[Path], None]  # bekommt den Paketpfad, bevor die erste Datei geschrieben wird


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


def _arcname(arcname: str) -> str:
    """Pfad im Paket: Unterordner erlaubt, je Teil nur sichere Zeichen, nie „..“ oder absolut."""
    parts = []
    for seg in arcname.split("/"):
        seg = _SAFE_SEGMENT.sub("-", seg).strip("-")[:120]
        if seg and seg not in (".", ".."):
            parts.append(seg)
    return "/".join(parts) or "unbenannt"


def _target(kind: str, name: str, source_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    base = f"{stamp}_{_safe(name, 40)}_{_safe(source_id, 8)}"
    folder = kind_dir(kind)
    candidate, n = folder / f"{base}.tar.gz", 1
    while candidate.exists() or candidate.with_name(candidate.name + ".part").exists():
        n += 1
        candidate = folder / f"{base}-{n}.tar.gz"
    return candidate


class _Packer:
    """Zählt Einträge mit und meldet Fortschritt. `skip` sind Pfade im Paket, die durch eine
    eigene Quelle ersetzt werden (z. B. config.json mit *** statt Geheimnis)."""

    def __init__(self, tar: tarfile.TarFile, skip: set[str], on_file: OnFile | None) -> None:
        self.tar, self.skip, self.on_file, self.entries = tar, skip, on_file, 0

    def add(self, path: Path, arcname: str) -> None:
        info = self.tar.gettarinfo(str(path), arcname=arcname)
        if info.isreg():
            with open(path, "rb") as fh:
                self.tar.addfile(info, fh)
            if self.on_file:
                self.on_file(info.size)
        else:
            self.tar.addfile(info)
        self.entries += 1


def _add_tree(packer: _Packer, arcname: str, source: Path) -> None:
    """Wie tar.add(recursive=True), aber ohne eingehängte Laufwerke. Symlinks
    werden als Symlinks gesichert (nicht verfolgt).

    Bewusst NICHT backup._paths.is_excluded: Das System-Backup lässt VM-Platten
    und Ordner wie vms/ oder tls/ weg. Ein Archiv soll vollständig sein: Was
    der Nutzer hatte, kommt mit."""
    packer.add(source, arcname)
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
            packer.add(p, f"{arcname}/{p.relative_to(source)}")
        dirs[:] = keep
        for f in sorted(files):
            p = here / f
            name = f"{arcname}/{p.relative_to(source)}"
            if name not in packer.skip:
                packer.add(p, name)


class ArchiveBusy(RuntimeError):
    """Das Archiv zieht gerade um – jetzt nichts hineinschreiben (Etappe 1b)."""


def pack(*, kind: str, name: str, source_id: str, owner: str | None, reason: str,
         sources: list[tuple[str, Path]], extra: dict[str, Any] | None = None,
         skip: set[str] | None = None, on_file: OnFile | None = None,
         on_target: OnTarget | None = None) -> dict:
    """Packt `sources` ([(arcname, pfad)]) ins Archiv. Gibt die .json-Daten zurück.

    `arcname` darf Unterordner haben („agents/<id>/agent“). `skip`: Dateien in den Ordnern, die
    nicht gepackt werden, weil eine eigene Quelle sie ersetzt. `on_target`: Pfad vorab melden, damit ein
    harter Abbruch (Neustart) das halbe Paket später findet."""
    if location.moving():
        raise ArchiveBusy("Archiv zieht gerade um")
    target = _target(kind, name, source_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    if on_target is not None:
        on_target(target)
    try:
        with open(part, "xb") as fh:
            writer = _HashingWriter(fh)
            with tarfile.open(fileobj=writer, mode="w:gz", compresslevel=settings.archive_compress_level) as tar:
                packer = _Packer(tar, {_arcname(s) for s in (skip or set())}, on_file)
                for arcname, src in sources:
                    if os.path.lexists(src):
                        _add_tree(packer, _arcname(arcname), Path(src))
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
        "size": target.stat().st_size, "sha256": writer.sha256.hexdigest(), "entries": packer.entries,
    }
    json_path = target.with_name(target.name + ".json")
    tmp = json_path.with_name(json_path.name + ".part")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, json_path)
    logger.info("Archiviert: %s/%s (%d Bytes, Grund %s)", kind, target.name, meta["size"], reason)
    return meta
