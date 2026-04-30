"""VM-Lifecycle: start/stop/poweroff via QEMU-Subprocess."""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
import signal
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.vms import vnc
from hydrahive.vms.db import get_vm, update_vm_state
from hydrahive.vms.ports import allocate_vnc_port
from hydrahive.vms.qemu_args import build_qemu_args, ensure_dirs

logger = logging.getLogger(__name__)


class VMLifecycleError(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


async def start(vm_id: str) -> None:
    """Startet QEMU als Daemon (-daemonize), liest PID aus Pidfile."""
    ensure_dirs()
    vm = get_vm(vm_id)
    if not vm:
        raise VMLifecycleError("vm_not_found", vm_id=vm_id)
    if vm.actual_state in ("running", "starting"):
        return  # idempotent
    if not Path(vm.qcow2_path).exists():
        raise VMLifecycleError("qcow2_missing", path=vm.qcow2_path)

    port = allocate_vnc_port()
    if port is None:
        raise VMLifecycleError("vnc_ports_exhausted")
    token = secrets.token_urlsafe(24)

    update_vm_state(vm_id, desired="running", actual="starting",
                    vnc_port=port, vnc_token=token,
                    error_code=None, error_params=None)

    args = build_qemu_args(vm, port)
    log_path = settings.vms_logs_dir / f"{vm.vm_id}.log"

    try:
        with log_path.open("ab") as logf:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args, stdout=logf, stderr=asyncio.subprocess.STDOUT,
                )
            except FileNotFoundError:
                update_vm_state(vm_id, actual="error",
                                error_code="qemu_system_missing", error_params={})
                raise VMLifecycleError("qemu_system_missing")
            rc = await asyncio.wait_for(proc.wait(), timeout=20.0)
        if rc != 0:
            tail = _tail(log_path, 20)
            update_vm_state(vm_id, actual="error",
                            error_code="qemu_start_failed",
                            error_params={"rc": rc, "log_tail": tail})
            raise VMLifecycleError("qemu_start_failed", rc=rc)
    except asyncio.TimeoutError:
        update_vm_state(vm_id, actual="error",
                        error_code="qemu_daemonize_timeout", error_params={})
        raise VMLifecycleError("qemu_daemonize_timeout")

    pid = _read_pid(vm_id)
    if pid is None or not _pid_alive(pid):
        update_vm_state(vm_id, actual="error",
                        error_code="qemu_died_after_start", error_params={})
        raise VMLifecycleError("qemu_died_after_start")

    # Token-File für websockify schreiben — erst NACHDEM QEMU als running
    # bestätigt ist. Vorher würde websockify auf einen toten Port routen.
    try:
        vnc.write_token(token, port)
    except (OSError, ValueError) as e:
        logger.warning("VNC-Token konnte nicht geschrieben werden: %s", e)

    update_vm_state(vm_id, actual="running", pid=pid)


async def shutdown(vm_id: str, *, hard: bool = False) -> None:
    """Graceful (SIGTERM, ACPI) oder hart (SIGKILL)."""
    vm = get_vm(vm_id)
    if not vm:
        raise VMLifecycleError("vm_not_found", vm_id=vm_id)
    if vm.pid is None or not _pid_alive(vm.pid):
        vnc.remove_token(vm.vnc_token)
        update_vm_state(vm_id, desired="stopped", actual="stopped", pid=None,
                        vnc_port=None, vnc_token=None)
        return
    update_vm_state(vm_id, desired="stopped", actual="stopping")
    try:
        os.kill(vm.pid, signal.SIGKILL if hard else signal.SIGTERM)
    except ProcessLookupError:
        pass
    # Reconciler räumt den Rest auf, aber wir warten kurz für UX-Feedback
    for _ in range(20 if not hard else 5):
        await asyncio.sleep(0.5)
        if not _pid_alive(vm.pid):
            break
    vnc.remove_token(vm.vnc_token)
    update_vm_state(vm_id, actual="stopped", pid=None,
                    vnc_port=None, vnc_token=None)


def _read_pid(vm_id: str) -> int | None:
    pidfile = settings.vms_pids_dir / f"{vm_id}.pid"
    try:
        return int(pidfile.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _tail(path: Path, lines: int) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
        return "\n".join(data.splitlines()[-lines:])
    except OSError:
        return ""
