"""DB-Zugriff für VMs — Mapping zu/von Dataclasses + simple CRUD."""
from __future__ import annotations

import json
import sqlite3
from typing import Iterable

from hydrahive.db.connection import db
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.vms.models import VM, ImportJob, Snapshot


def _row_to_vm(r: sqlite3.Row) -> VM:
    params = json.loads(r["last_error_params"]) if r["last_error_params"] else None
    return VM(
        vm_id=r["vm_id"], owner=r["owner"], name=r["name"], description=r["description"],
        cpu=r["cpu"], ram_mb=r["ram_mb"], disk_gb=r["disk_gb"],
        iso_filename=r["iso_filename"], network_mode=r["network_mode"],
        qcow2_path=r["qcow2_path"],
        desired_state=r["desired_state"], actual_state=r["actual_state"],
        pid=r["pid"], vnc_port=r["vnc_port"], vnc_token=r["vnc_token"],
        last_error_code=r["last_error_code"], last_error_params=params,
        created_at=r["created_at"], updated_at=r["updated_at"],
    )


def create_vm(owner: str, name: str, cpu: int, ram_mb: int, disk_gb: int,
              qcow2_path: str, network_mode: str = "bridged",
              description: str | None = None, iso_filename: str | None = None) -> VM:
    vm_id = uuid7()
    ts = now_iso()
    with db() as conn:
        conn.execute(
            """INSERT INTO vms (vm_id, owner, name, description, cpu, ram_mb, disk_gb,
                                iso_filename, network_mode, qcow2_path, desired_state,
                                actual_state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'stopped', 'created', ?, ?)""",
            (vm_id, owner, name, description, cpu, ram_mb, disk_gb,
             iso_filename, network_mode, qcow2_path, ts, ts),
        )
    return get_vm(vm_id)  # type: ignore[return-value]


def get_vm(vm_id: str) -> VM | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM vms WHERE vm_id = ?", (vm_id,)).fetchone()
    return _row_to_vm(row) if row else None


def list_vms(owner: str | None = None) -> list[VM]:
    with db() as conn:
        if owner is None:
            rows = conn.execute("SELECT * FROM vms ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM vms WHERE owner = ? ORDER BY created_at DESC",
                (owner,),
            ).fetchall()
    return [_row_to_vm(r) for r in rows]


def update_vm_state(vm_id: str, *, desired: str | None = None, actual: str | None = None,
                    pid: int | None = ..., vnc_port: int | None = ...,
                    vnc_token: str | None = ...,
                    error_code: str | None = ..., error_params: dict | None = ...) -> None:
    """Partial update — Sentinels (...) = nicht ändern, None = explizit auf NULL setzen."""
    sets: list[str] = ["updated_at = ?"]
    vals: list = [now_iso()]
    if desired is not None:
        sets.append("desired_state = ?"); vals.append(desired)
    if actual is not None:
        sets.append("actual_state = ?"); vals.append(actual)
    if pid is not ...:
        sets.append("pid = ?"); vals.append(pid)
    if vnc_port is not ...:
        sets.append("vnc_port = ?"); vals.append(vnc_port)
    if vnc_token is not ...:
        sets.append("vnc_token = ?"); vals.append(vnc_token)
    if error_code is not ...:
        sets.append("last_error_code = ?"); vals.append(error_code)
    if error_params is not ...:
        sets.append("last_error_params = ?")
        vals.append(json.dumps(error_params) if error_params else None)
    vals.append(vm_id)
    with db() as conn:
        conn.execute(f"UPDATE vms SET {', '.join(sets)} WHERE vm_id = ?", vals)


def delete_vm(vm_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM vms WHERE vm_id = ?", (vm_id,))


def name_taken(owner: str, name: str, exclude_id: str | None = None) -> bool:
    with db() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT 1 FROM vms WHERE owner = ? AND name = ? AND vm_id != ?",
                (owner, name, exclude_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM vms WHERE owner = ? AND name = ?", (owner, name),
            ).fetchone()
    return row is not None


def used_vnc_ports() -> set[int]:
    with db() as conn:
        rows = conn.execute(
            "SELECT vnc_port FROM vms WHERE vnc_port IS NOT NULL"
        ).fetchall()
    return {r["vnc_port"] for r in rows}
