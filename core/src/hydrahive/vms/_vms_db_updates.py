"""Partial-update helpers for VM state and config."""
from __future__ import annotations

import json

from hydrahive.db.connection import db
from hydrahive.db._utils import now_iso


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


def update_vm_config(vm_id: str, *, name: str | None = None, description: str | None = ...,
                     cpu: int | None = None, ram_mb: int | None = None,
                     disk_gb: int | None = None,
                     iso_filename: str | None = ...) -> None:
    """Konfig-Update für eine VM. Nur im stopped-State erlaubt — der Caller validiert.
    Sentinels (...) für optionale clear-zu-NULL."""
    sets: list[str] = ["updated_at = ?"]
    vals: list = [now_iso()]
    if name is not None:
        sets.append("name = ?"); vals.append(name)
    if description is not ...:
        sets.append("description = ?"); vals.append(description)
    if cpu is not None:
        sets.append("cpu = ?"); vals.append(cpu)
    if ram_mb is not None:
        sets.append("ram_mb = ?"); vals.append(ram_mb)
    if disk_gb is not None:
        sets.append("disk_gb = ?"); vals.append(disk_gb)
    if iso_filename is not ...:
        sets.append("iso_filename = ?"); vals.append(iso_filename)
    vals.append(vm_id)
    with db() as conn:
        conn.execute(f"UPDATE vms SET {', '.join(sets)} WHERE vm_id = ?", vals)
