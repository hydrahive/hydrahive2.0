"""Dispatch container operations to the local Incus host or a remote node job."""

from __future__ import annotations

from hydrahive.containers import db as cdb
from hydrahive.containers import lifecycle, remote
from hydrahive.containers.incus_client import IncusError


def _container(container_id: str):
    container = cdb.get(container_id)
    if container is None:
        raise IncusError("container_not_found", id=container_id)
    return container


async def create_and_start(container_id: str, *, actor: str) -> None:
    container = _container(container_id)
    if container.node_id == "local":
        await lifecycle.create_and_start(container_id)
    else:
        remote.queue_create(container_id, actor=actor)


async def start(container_id: str, *, actor: str) -> None:
    container = _container(container_id)
    if container.node_id == "local":
        await lifecycle.start(container_id)
    else:
        remote.queue_lifecycle(container_id, "container.start", actor=actor)


async def stop(container_id: str, *, actor: str, force: bool = False) -> None:
    container = _container(container_id)
    if container.node_id == "local":
        await lifecycle.stop(container_id, force=force)
    else:
        remote.queue_lifecycle(container_id, "container.stop", actor=actor)


async def restart(container_id: str, *, actor: str) -> None:
    container = _container(container_id)
    if container.node_id == "local":
        await lifecycle.restart_(container_id)
    else:
        remote.queue_lifecycle(container_id, "container.restart", actor=actor)


async def delete(container_id: str, *, actor: str) -> None:
    container = cdb.get(container_id)
    if container is None:
        return
    if container.node_id == "local":
        await lifecycle.delete(container_id)
    else:
        remote.queue_lifecycle(container_id, "container.delete", actor=actor)
