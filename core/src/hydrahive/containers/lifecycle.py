"""Container-Lifecycle: launch/start/stop/delete via incus_client."""
from __future__ import annotations

import logging

from hydrahive.settings import settings
from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus

logger = logging.getLogger(__name__)


def _bridge() -> str:
    return settings.vms_bridge  # br0 — Default für VMs UND Container


async def create_and_start(container_id: str) -> None:
    c = cdb.get(container_id)
    if not c:
        raise incus.IncusError("container_not_found", id=container_id)
    cdb.update_state(container_id, desired="running", actual="starting",
                     error_code=None, error_params=None)
    try:
        await incus.launch(
            c.name, c.image,
            network_mode=c.network_mode,
            cpu=c.cpu, ram_mb=c.ram_mb,
            bridge=_bridge(),
        )
    except incus.IncusError as e:
        cdb.update_state(container_id, actual="error",
                         error_code=e.code, error_params=e.params)
        raise
    cdb.update_state(container_id, actual="running")


async def start(container_id: str) -> None:
    c = cdb.get(container_id)
    if not c:
        raise incus.IncusError("container_not_found", id=container_id)
    cdb.update_state(container_id, desired="running", actual="starting",
                     error_code=None, error_params=None)
    try:
        await incus.start(c.name)
    except incus.IncusError as e:
        cdb.update_state(container_id, actual="error",
                         error_code=e.code, error_params=e.params)
        raise
    cdb.update_state(container_id, actual="running")


async def stop(container_id: str, *, force: bool = False) -> None:
    c = cdb.get(container_id)
    if not c:
        raise incus.IncusError("container_not_found", id=container_id)
    cdb.update_state(container_id, desired="stopped", actual="stopping")
    try:
        await incus.stop(c.name, force=force)
    except incus.IncusError as e:
        cdb.update_state(container_id, actual="error",
                         error_code=e.code, error_params=e.params)
        raise
    cdb.update_state(container_id, actual="stopped")


async def restart_(container_id: str) -> None:
    c = cdb.get(container_id)
    if not c:
        raise incus.IncusError("container_not_found", id=container_id)
    await incus.restart_(c.name)
    cdb.update_state(container_id, actual="running",
                     error_code=None, error_params=None)


async def delete(container_id: str) -> None:
    c = cdb.get(container_id)
    if not c:
        return
    try:
        await incus.delete(c.name, force=True)
    except incus.IncusError:
        # incus weg, aber DB sauber halten
        pass
    cdb.delete(container_id)
