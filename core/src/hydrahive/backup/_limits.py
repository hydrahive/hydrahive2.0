"""Größen-Caps für Restore-Uploads + Extraktion (Issue #189).

Schützt gegen Disk-Fill durch große Uploads und gegen Dekompressionsbomben
(wenige MB gzip → viele GB entpackt). VMs/Container sind ohnehin vom Backup
ausgenommen, daher sind diese Defaults großzügig, aber endlich.
"""
from __future__ import annotations

import tarfile
from pathlib import Path

MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024      # 2 GiB komprimierter Upload
MAX_EXTRACTED_BYTES = 8 * 1024 * 1024 * 1024   # 8 GiB entpackt (Bomben-Schutz)
MAX_MEMBERS = 100_000

_CHUNK = 1024 * 1024


class RestoreTooLarge(Exception):
    def __init__(self, code: str, **params):
        self.code = code
        self.params = params
        super().__init__(code)


async def stream_upload_capped(upload, dest_path: Path, *, max_bytes: int | None = None) -> None:
    """Streamt einen Upload chunked auf Platte, bricht bei Überschreitung ab."""
    limit = max_bytes if max_bytes is not None else MAX_UPLOAD_BYTES
    total = 0
    with dest_path.open("wb") as f:
        while True:
            chunk = await upload.read(_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise RestoreTooLarge("backup_upload_too_large", limit=limit)
            f.write(chunk)


def enforce_archive_limits(tar: tarfile.TarFile, *, max_bytes: int | None = None,
                           max_members: int | None = None) -> None:
    """Prüft kumulierte entpackte Größe + Member-Anzahl, BEVOR extractall läuft."""
    byte_cap = max_bytes if max_bytes is not None else MAX_EXTRACTED_BYTES
    member_cap = max_members if max_members is not None else MAX_MEMBERS
    total = 0
    count = 0
    for member in tar.getmembers():
        count += 1
        if count > member_cap:
            raise RestoreTooLarge("backup_too_many_members", limit=member_cap)
        total += max(0, member.size)
        if total > byte_cap:
            raise RestoreTooLarge("backup_extracted_too_large", limit=byte_cap)
