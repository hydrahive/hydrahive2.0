"""Helpers for project server assignment routes."""
from __future__ import annotations

from typing import Literal

from fastapi import status
from pydantic import BaseModel

from hydrahive.api.middleware.errors import coded
from hydrahive.projects import config as project_config

ServerKind = Literal["vm", "container"]


class AssignRequest(BaseModel):
    kind: ServerKind
    id: str


def project_or_404(project_id: str, username: str, role: str, required: str = "read") -> dict:
    """Projekt laden und Mindestrolle prüfen (read < write < admin, docs/specs/project-member-roles.md)."""
    from hydrahive.api.routes._project_route_helpers import check_project_access
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, username, role, required)
    return p


def vm_dict(vm) -> dict:
    return {
        "kind": "vm", "id": vm.vm_id, "name": vm.name, "owner": vm.owner,
        "desired_state": vm.desired_state, "actual_state": vm.actual_state,
        "cpu": vm.cpu, "ram_mb": vm.ram_mb, "disk_gb": vm.disk_gb,
        "network_mode": vm.network_mode, "project_id": vm.project_id,
    }


def container_dict(c) -> dict:
    return {
        "kind": "container", "id": c.container_id, "name": c.name, "owner": c.owner,
        "desired_state": c.desired_state, "actual_state": c.actual_state,
        "image": c.image, "cpu": c.cpu, "ram_mb": c.ram_mb,
        "network_mode": c.network_mode, "project_id": c.project_id,
    }
