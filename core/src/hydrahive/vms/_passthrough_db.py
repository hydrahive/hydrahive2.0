"""Persistence helpers for VM passthrough disks and VM generations."""

from __future__ import annotations

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.vms.models import PassthroughDisk


def _row_to_passthrough(row) -> PassthroughDisk:
    return PassthroughDisk(
        passthrough_id=row["passthrough_id"],
        vm_id=row["vm_id"],
        device_path=row["device_path"],
        label=row["label"],
        added_at=row["added_at"],
    )


def list_for_vm(vm_id: str) -> list[PassthroughDisk]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM vm_passthrough_disks WHERE vm_id = ? ORDER BY added_at",
            (vm_id,),
        ).fetchall()
    return [_row_to_passthrough(row) for row in rows]


def list_all_paths() -> set[str]:
    with db() as conn:
        rows = conn.execute("SELECT device_path FROM vm_passthrough_disks").fetchall()
    return {row["device_path"] for row in rows}


def insert(vm_id: str, device_path: str, label: str | None) -> PassthroughDisk:
    passthrough_id = uuid7()
    timestamp = now_iso()
    with db() as conn:
        conn.execute(
            """INSERT INTO vm_passthrough_disks
                   (passthrough_id, vm_id, device_path, label, added_at)
               VALUES (?, ?, ?, ?, ?)""",
            (passthrough_id, vm_id, device_path, label, timestamp),
        )
        conn.execute(
            "UPDATE vms SET generation = generation + 1, updated_at = ? WHERE vm_id = ?",
            (timestamp, vm_id),
        )
    return PassthroughDisk(
        passthrough_id=passthrough_id,
        vm_id=vm_id,
        device_path=device_path,
        label=label,
        added_at=timestamp,
    )


def remove(vm_id: str, passthrough_id: str) -> bool:
    timestamp = now_iso()
    with db() as conn:
        result = conn.execute(
            "DELETE FROM vm_passthrough_disks WHERE passthrough_id = ? AND vm_id = ?",
            (passthrough_id, vm_id),
        )
        if result.rowcount:
            conn.execute(
                "UPDATE vms SET generation = generation + 1, updated_at = ? WHERE vm_id = ?",
                (timestamp, vm_id),
            )
    return result.rowcount > 0
