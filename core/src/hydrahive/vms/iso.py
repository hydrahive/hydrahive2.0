"""ISO-Upload + Validierung + Listing.

Validiert via ISO-9660 Magic Bytes (Sector 16 = Byte 32768, "CD001" Marker).
Speichert nach Sanitize unter `vms_isos_dir`. Sha256 als Identifier.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from hydrahive.db._utils import now_iso
from hydrahive.settings import settings
from hydrahive.vms.models import ISO

ISO9660_MAGIC = b"CD001"
ISO9660_OFFSET = 32768  # Sector 16 + 1 byte (descriptor type)
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")
MAX_ISO_BYTES = 8 * 1024 * 1024 * 1024  # 8 GB Cap pro ISO


class ISOError(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


def safe_filename(name: str) -> str:
    """Entfernt Pfad-Trenner, .. und Sonderzeichen."""
    base = Path(name).name  # entfernt Pfad
    cleaned = SAFE_NAME_RE.sub("_", base)
    if not cleaned or cleaned in (".", ".."):
        raise ISOError("iso_invalid_name", name=name)
    if not cleaned.lower().endswith(".iso"):
        cleaned += ".iso"
    return cleaned


def validate_iso9660(path: Path) -> None:
    """Wirft ISOError wenn die Datei nicht ISO-9660-aussieht."""
    try:
        with path.open("rb") as f:
            f.seek(ISO9660_OFFSET + 1)  # +1 = überspringe descriptor type byte
            magic = f.read(5)
        if magic != ISO9660_MAGIC:
            raise ISOError("iso_invalid_format", magic=magic.decode("ascii", "replace"))
    except OSError as e:
        raise ISOError("iso_read_failed", error=str(e))


async def save_upload_stream(filename: str, source) -> ISO:
    """Streamt UploadFile-artigen Source in die ISO-Library.

    `source` muss eine async read(n)-Methode haben (FastAPI UploadFile).
    """
    settings.vms_isos_dir.mkdir(parents=True, exist_ok=True)
    name = safe_filename(filename)
    target = settings.vms_isos_dir / name
    if target.exists():
        raise ISOError("iso_already_exists", filename=name)
    h = hashlib.sha256()
    total = 0
    chunk = 1024 * 1024
    try:
        with target.open("wb") as f:
            while True:
                buf = await source.read(chunk)
                if not buf:
                    break
                total += len(buf)
                if total > MAX_ISO_BYTES:
                    raise ISOError("iso_too_large", size=total, max=MAX_ISO_BYTES)
                h.update(buf)
                f.write(buf)
        validate_iso9660(target)
    except (ISOError, OSError):
        target.unlink(missing_ok=True)
        raise
    return ISO(
        filename=name, size_bytes=total, sha256=h.hexdigest(),
        uploaded_at=now_iso(),
    )


def _hash_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def list_isos(*, with_hash: bool = False) -> list[ISO]:
    """Listet ISOs. with_hash=True liest jede Datei (langsam bei großen ISOs)."""
    if not settings.vms_isos_dir.exists():
        return []
    out: list[ISO] = []
    for p in sorted(settings.vms_isos_dir.glob("*.iso")):
        try:
            stat = p.stat()
        except OSError:
            continue
        out.append(ISO(
            filename=p.name,
            size_bytes=stat.st_size,
            sha256=_hash_file(p) if with_hash else "",
            uploaded_at=_iso_mtime(stat.st_mtime),
        ))
    return out


def _iso_mtime(epoch: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")


def delete_iso(filename: str) -> None:
    name = safe_filename(filename)
    target = settings.vms_isos_dir / name
    if not target.exists():
        raise ISOError("iso_not_found", filename=name)
    target.unlink()
