"""Dispatch VM operations to the local QEMU host or a remote node job.

Local VMs (``runtime == "qemu"``) keep their existing lifecycle. Remote image
VMs (``runtime == "incus"`` on an agent node) are driven through durable,
generation-bound compute jobs.
"""

from __future__ import annotations

from hydrahive.vms import db as vmdb
from hydrahive.vms import lifecycle, remote
from hydrahive.vms.lifecycle import VMLifecycleError


def _vm(vm_id: str):
    vm = vmdb.get_vm(vm_id)
    if vm is None:
        raise VMLifecycleError("vm_not_found", vm_id=vm_id)
    return vm


def is_remote(vm) -> bool:
    return vm.node_id != "local" or vm.runtime != "qemu"


async def create_and_start(vm_id: str, *, actor: str) -> None:
    vm = _vm(vm_id)
    if is_remote(vm):
        remote.queue_create(vm_id, actor=actor)
    # Local VM creation stays inline in the create route (disk provisioning).


async def start(vm_id: str, *, actor: str) -> None:
    vm = _vm(vm_id)
    if is_remote(vm):
        remote.queue_lifecycle(vm_id, "vm.start", actor=actor)
    else:
        await lifecycle.start(vm_id)


async def stop(vm_id: str, *, actor: str, hard: bool = False) -> None:
    vm = _vm(vm_id)
    if is_remote(vm):
        remote.queue_lifecycle(vm_id, "vm.stop", actor=actor)
    else:
        await lifecycle.shutdown(vm_id, hard=hard)


async def restart(vm_id: str, *, actor: str) -> None:
    vm = _vm(vm_id)
    if is_remote(vm):
        remote.queue_lifecycle(vm_id, "vm.restart", actor=actor)
    else:
        await lifecycle.shutdown(vm_id, hard=True)
        await lifecycle.start(vm_id)


async def delete(vm_id: str, *, actor: str) -> None:
    vm = vmdb.get_vm(vm_id)
    if vm is None:
        return
    if is_remote(vm):
        remote.queue_lifecycle(vm_id, "vm.delete", actor=actor)
    # Local VM deletion stays inline in the delete route (disk cleanup).
