"""Portfreigaben für NAT-Container (docs/specs/container-nat-ports.md).

Wie alle Container-Routen hinter core.containers (api/main.py). Öffentliche
Freigaben (scope=public) darf zusätzlich nur ein Admin setzen: Sie öffnen den
Server ins Internet.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._container_helpers import container_or_404, is_admin
from hydrahive.containers import incus_client as incus
from hydrahive.containers import nat
from hydrahive.containers import ports as cports
from hydrahive.containers.models import Container

router = APIRouter(prefix="/api/containers", tags=["containers"])

_Auth = Annotated[tuple[str, str], Depends(require_auth)]
Scope = Literal["public", "tailnet", "off"]


class PortCreate(BaseModel):
    protocol: Literal["tcp", "udp"]
    host_port_start: int = Field(ge=1, le=65535)
    host_port_end: int | None = Field(default=None, ge=1, le=65535)
    container_port_start: int | None = Field(default=None, ge=1, le=65535)
    scope: Scope = "off"
    label: str = Field(default="", max_length=64)


class PortPatch(BaseModel):
    scope: Scope


def _nat_container(container_id: str, auth: tuple[str, str]) -> tuple[Container, str]:
    c = container_or_404(container_id, *auth)
    ip = nat.get_ipv4(container_id) if c.network_mode == "nat" else None
    if c.node_id != "local" or not ip:
        raise coded(status.HTTP_400_BAD_REQUEST, "container_port_not_nat")
    return c, ip


def _check_public(scope: str, role: str) -> None:
    if scope == "public" and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "container_port_public_forbidden")


def _raise(exc: Exception):
    if isinstance(exc, cports.PortError):
        code = status.HTTP_409_CONFLICT if exc.code == "container_port_conflict" else status.HTTP_400_BAD_REQUEST
        if exc.code == "container_port_apply_failed":
            code = status.HTTP_502_BAD_GATEWAY
        params = {k: v for k, v in exc.params.items() if k != "detail"}
        raise coded(code, exc.code, **params)
    raise coded(status.HTTP_502_BAD_GATEWAY, "container_port_apply_failed")


@router.get("/{container_id}/ports")
def list_ports(container_id: str, auth: _Auth) -> dict:
    c = container_or_404(container_id, *auth)
    return {
        "ipv4": nat.get_ipv4(container_id),
        "network_mode": c.network_mode,
        "ports": [r.to_dict() for r in cports.list_for(container_id)],
    }


@router.post("/{container_id}/ports", status_code=status.HTTP_201_CREATED)
async def add_port(container_id: str, body: PortCreate, auth: _Auth) -> dict:
    c, ip = _nat_container(container_id, auth)
    _check_public(body.scope, auth[1])
    end = body.host_port_end or body.host_port_start
    cstart = body.container_port_start or body.host_port_start
    try:
        rule = cports.create(container_id, body.protocol, body.host_port_start, end, cstart, body.scope, body.label)
    except cports.PortError as exc:
        _raise(exc)
    try:
        await cports.apply(c.name, ip, rule)
    except (cports.PortError, incus.IncusError) as exc:
        _raise(exc)
    return cports.get(rule.id).to_dict()  # type: ignore[union-attr]


@router.patch("/{container_id}/ports/{port_id}")
async def set_scope(container_id: str, port_id: str, body: PortPatch, auth: _Auth) -> dict:
    c, ip = _nat_container(container_id, auth)
    rule = cports.get(port_id)
    if not rule or rule.container_id != container_id:
        raise coded(status.HTTP_404_NOT_FOUND, "container_port_not_found")
    _check_public(body.scope, auth[1])
    rule = cports.set_scope(port_id, body.scope)
    try:
        await cports.apply(c.name, ip, rule)  # type: ignore[arg-type]
    except (cports.PortError, incus.IncusError) as exc:
        _raise(exc)
    return cports.get(port_id).to_dict()  # type: ignore[union-attr]


@router.delete("/{container_id}/ports/{port_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port(container_id: str, port_id: str, auth: _Auth) -> None:
    c, _ip = _nat_container(container_id, auth)
    rule = cports.get(port_id)
    if not rule or rule.container_id != container_id:
        raise coded(status.HTTP_404_NOT_FOUND, "container_port_not_found")
    try:
        await cports.remove(c.name, rule)
    except (cports.PortError, incus.IncusError) as exc:
        _raise(exc)
    cports.delete_row(port_id)
