"""Reconciliation-Loop: gleicht actual_state mit der Realität ab.

Alle ~3s: für jede VM mit aktivem Zustand (running/starting/stopping) wird
geprüft ob der Prozess noch lebt. Tote Prozesse werden auf 'stopped' bzw.
'error' gesetzt, VNC-Tokens und Ports freigegeben. Token-Files ohne lebende
VM werden aufgeräumt.

Idee: Frontend sieht IMMER die Wahrheit, auch nach Crash, kill -9 oder Reboot
des Hosts. Kein Drift zwischen DB-State und realem QEMU-Prozess.
"""
from __future__ import annotations

import asyncio
import logging
import os

from hydrahive.vms import vnc
from hydrahive.vms.db import list_vms, update_vm_state

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 3.0
ACTIVE_STATES = ("running", "starting", "stopping")


def _pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


async def reconcile_once() -> None:
    """Ein Durchlauf — wird vom Loop und auf Wunsch direkt aufgerufen."""
    try:
        vms = list_vms(owner=None)
    except Exception as e:
        logger.exception("Reconciler: list_vms fehlgeschlagen: %s", e)
        return

    active_tokens: set[str] = set()
    for vm in vms:
        if vm.actual_state not in ACTIVE_STATES:
            continue
        alive = _pid_alive(vm.pid)
        if alive and vm.vnc_token:
            active_tokens.add(vm.vnc_token)
            continue
        if not alive:
            logger.info("Reconciler: VM %s (%s) Prozess tot — markiere stopped",
                        vm.name, vm.vm_id)
            new_state = "error" if vm.desired_state == "running" else "stopped"
            err_code = "qemu_process_died" if new_state == "error" else None
            update_vm_state(
                vm.vm_id, actual=new_state, pid=None,
                vnc_port=None, vnc_token=None,
                error_code=err_code,
                error_params={} if err_code else None,
            )
            vnc.remove_token(vm.vnc_token)

    # Orphan-Tokens aufräumen — Token-Files ohne dazugehörige laufende VM
    try:
        vnc.cleanup_orphans(active_tokens)
    except OSError:
        logger.exception("Reconciler: Orphan-Token-Cleanup fehlgeschlagen")


async def run_loop(stop: asyncio.Event) -> None:
    """Endless-Loop bis stop gesetzt. Vom Lifespan gestartet."""
    logger.info("VM-Reconciler gestartet (Intervall %.1fs)", POLL_INTERVAL_S)
    while not stop.is_set():
        await reconcile_once()
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_INTERVAL_S)
        except asyncio.TimeoutError:
            pass
    logger.info("VM-Reconciler beendet")
