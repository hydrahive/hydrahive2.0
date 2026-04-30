"""qcow2-Snapshots via qemu-img snapshot.

Offline-Only: VM muss gestoppt sein. Live-Snapshots würden QMP brauchen
(savevm/loadvm) — kommt später wenn überhaupt nötig.

`qemu-img snapshot -c <name> <file>`     — create
`qemu-img snapshot -l <file>`            — list
`qemu-img snapshot -a <name> <file>`     — apply (restore)
`qemu-img snapshot -d <name> <file>`     — delete
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


SNAPSHOT_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")


class SnapshotError(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


def validate_name(name: str) -> None:
    if not SNAPSHOT_NAME_RE.match(name):
        raise SnapshotError("snapshot_name_invalid", name=name)


async def _qemu_img(*args: str) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "qemu-img", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise SnapshotError("qemu_img_missing")
    out, err = await asyncio.wait_for(proc.communicate(), timeout=120.0)
    return (
        proc.returncode or 0,
        out.decode(errors="replace"),
        err.decode(errors="replace"),
    )


async def create(qcow2: Path, name: str) -> int:
    """Snapshot erstellen, return: Größe vom Snapshot in Bytes (best-effort)."""
    validate_name(name)
    rc, _, err = await _qemu_img("snapshot", "-c", name, str(qcow2))
    if rc != 0:
        raise SnapshotError("snapshot_create_failed", rc=rc, stderr=err[:300])
    # Größe nachträglich aus list ablesen
    rc, out, _ = await _qemu_img("snapshot", "-l", str(qcow2))
    if rc != 0:
        return 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == name:
            return _parse_size(parts[2])
    return 0


async def restore(qcow2: Path, name: str) -> None:
    validate_name(name)
    rc, _, err = await _qemu_img("snapshot", "-a", name, str(qcow2))
    if rc != 0:
        raise SnapshotError("snapshot_restore_failed", rc=rc, stderr=err[:300])


async def delete(qcow2: Path, name: str) -> None:
    validate_name(name)
    rc, _, err = await _qemu_img("snapshot", "-d", name, str(qcow2))
    if rc != 0:
        raise SnapshotError("snapshot_delete_failed", rc=rc, stderr=err[:300])


def _parse_size(s: str) -> int:
    """qemu-img snapshot -l zeigt Größen wie '1.2G' oder '512M'."""
    s = s.strip()
    if not s:
        return 0
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    if s[-1] in units:
        try:
            return int(float(s[:-1]) * units[s[-1]])
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0


# --- DB-Funktionen ---------------------------------------------------------

def db_create(vm_id: str, name: str, size_bytes: int,
              description: str | None = None) -> str:
    sid = uuid7()
    with db() as conn:
        conn.execute(
            """INSERT INTO vm_snapshots (snapshot_id, vm_id, name, description,
                                          size_bytes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sid, vm_id, name, description, size_bytes, now_iso()),
        )
    return sid


def db_list(vm_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM vm_snapshots WHERE vm_id = ? ORDER BY created_at DESC",
            (vm_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def db_get(snapshot_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM vm_snapshots WHERE snapshot_id = ?", (snapshot_id,),
        ).fetchone()
    return dict(row) if row else None


def db_delete(snapshot_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM vm_snapshots WHERE snapshot_id = ?", (snapshot_id,))
