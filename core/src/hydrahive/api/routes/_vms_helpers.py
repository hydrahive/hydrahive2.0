"""Geteilte Helpers für die vms_*-Sub-Router.

Auth-Check + 404/403-Resolution + Serialisierung + Create-Input-Validation.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import status

from hydrahive.api.middleware.errors import coded
from hydrahive.vms import db as vmdb
from hydrahive.vms import import_job as vmimport
from hydrahive.vms import iso as vmiso


def is_admin(role: str) -> bool:
    return role == "admin"


def vm_or_404(vm_id: str, owner: str, role: str):
    vm = vmdb.get_vm(vm_id)
    if not vm:
        raise coded(status.HTTP_404_NOT_FOUND, "vm_not_found")
    if vm.owner != owner and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    return vm


def serialize(vm) -> dict:
    return asdict(vm)


def resolve_iso(iso_filename: str | None) -> str | None:
    if not iso_filename:
        return None
    try:
        iso_safe = vmiso.safe_filename(iso_filename)
    except vmiso.ISOError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    if not (vmiso.settings.vms_isos_dir / iso_safe).exists():
        raise coded(status.HTTP_400_BAD_REQUEST, "iso_not_found", filename=iso_filename)
    return iso_safe


def resolve_import_job(job_id: str | None, user: str, role: str) -> Path | None:
    if not job_id:
        return None
    job = vmimport.db_get(job_id)
    if not job:
        raise coded(status.HTTP_404_NOT_FOUND, "import_job_not_found")
    if job["owner"] != user and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    if job["status"] != "done":
        raise coded(status.HTTP_409_CONFLICT, "import_job_not_done", status_=job["status"])
    qcow2 = Path(job["target_qcow2"])
    if not qcow2.exists():
        raise coded(status.HTTP_410_GONE, "import_qcow2_missing", path=str(qcow2))
    return qcow2
