"""Server-Assignments pro Projekt — VMs + Container.

Eine VM/ein Container kann max einem Projekt zugewiesen sein. Beim
Projekt-Löschen wird project_id auf NULL gesetzt — die Server selbst
bleiben dem Owner erhalten."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._server_route_helpers import (
    AssignRequest, ServerKind, container_dict as _container_dict,
    project_or_404 as _project_or_404, vm_dict as _vm_dict,
)
from hydrahive.containers import db as containers_db
from hydrahive.vms import db as vms_db

router = APIRouter(prefix="/api/projects", tags=["projects"])


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
