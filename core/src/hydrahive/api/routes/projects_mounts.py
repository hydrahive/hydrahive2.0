"""SMB-Mount-Zuweisung pro Projekt — assign mountet, unassign umountet.

Spiegelt projects_servers.py. Beim Assign wird das Share tatsächlich in
workspace/mounts/<name> gemountet; beim Unassign wieder ausgehängt.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._server_route_helpers import (
    project_or_404 as _project_or_404,
)
from hydrahive.api.routes._smbmount_helpers import AssignMountRequest, mount_dict
from hydrahive.projects import audit as project_audit
from hydrahive.smbmounts import db as mounts_db
from hydrahive.smbmounts import mounter

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/{project_id}/mounts")
def list_assigned(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    _project_or_404(project_id, *auth)
    return [mount_dict(m) for m in mounts_db.list_for_project(project_id)]


@router.get("/{project_id}/mounts/available")
def list_available(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    """Mounts des Users die noch keinem Projekt zugewiesen sind."""
    username, role = auth
    _project_or_404(project_id, username, role)
    owner = None if role == "admin" else username
    return [
        mount_dict(m) for m in mounts_db.list_mounts(owner=owner)
        if not m.project_id
    ]


@router.post("/{project_id}/mounts/assign")
def assign_mount(
    project_id: str,
    req: AssignMountRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, role = auth
    _project_or_404(project_id, username, role)
    m = mounts_db.get_mount(req.id)
    if not m:
        raise coded(404, "mount_not_found")
    if role != "admin" and m.owner != username:
        raise coded(403, "mount_no_access")
    if m.project_id and m.project_id != project_id:
        raise coded(409, "mount_already_assigned", project_id=m.project_id)

    mounts_db.set_project(req.id, project_id)
    mounts_db.set_state(req.id, "mounting")
    fresh = mounts_db.get_mount(req.id)
    ok, result = mounter.mount(fresh)
    if not ok:
        mounts_db.set_state(req.id, "error", error_code=result)
        mounts_db.set_project(req.id, None)
        raise coded(502, result)
    mounts_db.set_state(req.id, "mounted")
    project_audit.log(project_id, username, "mount_assigned",
                      target=f"smb:{req.id}")
    return mount_dict(mounts_db.get_mount(req.id))


@router.delete("/{project_id}/mounts/{mount_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def unassign_mount(
    project_id: str,
    mount_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    username, role = auth
    _project_or_404(project_id, username, role)
    m = mounts_db.get_mount(mount_id)
    if not m or m.project_id != project_id:
        raise coded(404, "mount_not_assigned")
    if role != "admin" and m.owner != username:
        raise coded(403, "mount_no_access")

    ok, result = mounter.umount(m)
    if not ok:
        mounts_db.set_state(mount_id, "error", error_code=result)
        raise coded(502, result)
    mounts_db.set_project(mount_id, None)
    mounts_db.set_state(mount_id, "unmounted")
    project_audit.log(project_id, username, "mount_unassigned",
                      target=f"smb:{mount_id}")
