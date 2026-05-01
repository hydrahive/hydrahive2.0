"""Server-Assignments pro Projekt — VMs + Container.

Eine VM/ein Container kann max einem Projekt zugewiesen sein. Beim
Projekt-Löschen wird project_id auf NULL gesetzt — die Server selbst
bleiben dem Owner erhalten."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.containers import db as containers_db
from hydrahive.projects import config as project_config
from hydrahive.vms import db as vms_db

router = APIRouter(prefix="/api/projects", tags=["projects"])

ServerKind = Literal["vm", "container"]


class AssignRequest(BaseModel):
    kind: ServerKind
    id: str


def _project_or_404(project_id: str, username: str, role: str) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    if role != "admin" and username not in p.get("members", []) and p.get("created_by") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")
    return p


def _vm_dict(vm) -> dict:
    return {
        "kind": "vm",
        "id": vm.vm_id,
        "name": vm.name,
        "owner": vm.owner,
        "desired_state": vm.desired_state,
        "actual_state": vm.actual_state,
        "cpu": vm.cpu,
        "ram_mb": vm.ram_mb,
        "disk_gb": vm.disk_gb,
        "network_mode": vm.network_mode,
        "project_id": vm.project_id,
    }


def _container_dict(c) -> dict:
    return {
        "kind": "container",
        "id": c.container_id,
        "name": c.name,
        "owner": c.owner,
        "desired_state": c.desired_state,
        "actual_state": c.actual_state,
        "image": c.image,
        "cpu": c.cpu,
        "ram_mb": c.ram_mb,
        "network_mode": c.network_mode,
        "project_id": c.project_id,
    }


@router.get("/{project_id}/servers")
def list_assigned(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    _project_or_404(project_id, *auth)
    out: list[dict] = []
    for vm in vms_db.list_for_project(project_id):
        out.append(_vm_dict(vm))
    for c in containers_db.list_for_project(project_id):
        out.append(_container_dict(c))
    return out


@router.get("/{project_id}/servers/available")
def list_available(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    """VMs/Container des Users die noch keinem Projekt zugewiesen sind."""
    username, role = auth
    _project_or_404(project_id, username, role)
    out: list[dict] = []
    owner = None if role == "admin" else username
    for vm in vms_db.list_vms(owner=owner):
        if not vm.project_id:
            out.append(_vm_dict(vm))
    for c in containers_db.list_(owner=owner):
        if not c.project_id:
            out.append(_container_dict(c))
    return out


@router.post("/{project_id}/servers/assign")
def assign_server(
    project_id: str,
    req: AssignRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, role = auth
    _project_or_404(project_id, username, role)
    if req.kind == "vm":
        vm = vms_db.get_vm(req.id)
        if not vm:
            raise coded(404, "vm_not_found")
        if role != "admin" and vm.owner != username:
            raise coded(403, "vm_no_access")
        if vm.project_id and vm.project_id != project_id:
            raise coded(409, "server_already_assigned", project_id=vm.project_id)
        vms_db.set_project(req.id, project_id)
    else:
        c = containers_db.get(req.id)
        if not c:
            raise coded(404, "container_not_found")
        if role != "admin" and c.owner != username:
            raise coded(403, "container_no_access")
        if c.project_id and c.project_id != project_id:
            raise coded(409, "server_already_assigned", project_id=c.project_id)
        containers_db.set_project(req.id, project_id)
    return {"ok": True}


@router.delete("/{project_id}/servers/{kind}/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_server(
    project_id: str,
    kind: ServerKind,
    server_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    username, role = auth
    _project_or_404(project_id, username, role)
    if kind == "vm":
        vm = vms_db.get_vm(server_id)
        if not vm or vm.project_id != project_id:
            raise coded(404, "server_not_assigned")
        if role != "admin" and vm.owner != username:
            raise coded(403, "vm_no_access")
        vms_db.set_project(server_id, None)
    else:
        c = containers_db.get(server_id)
        if not c or c.project_id != project_id:
            raise coded(404, "server_not_assigned")
        if role != "admin" and c.owner != username:
            raise coded(403, "container_no_access")
        containers_db.set_project(server_id, None)
