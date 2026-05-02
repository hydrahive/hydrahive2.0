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


def project_or_404(project_id: str, username: str, role: str) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    if role != "admin" and username not in p.get("members", []) and p.get("created_by") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")
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
