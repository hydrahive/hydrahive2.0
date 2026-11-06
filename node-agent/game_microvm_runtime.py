"""Low-level Incus probes for the Game Studio PR-0 proof harness."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import selectors
import subprocess
import time
from pathlib import Path

from game_microvm_contract import ProofConfig, ProofConfigurationError, allowed_guest_environment, forbidden_host_devices
from hydrahive_node import incus
from hydrahive_node.jobs import VerifiedJob

INCUS = Path("/usr/bin/incus")
KVM = Path("/dev/kvm")
MAX_HOST_OUTPUT_BYTES = 256 * 1024
FIXTURE_NAMES = {"export_presets.cfg", "main.gd", "main.tscn", "project.godot"}


class ProofExecutionError(RuntimeError):
    pass


def run_incus(*args: str, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    command = [str(INCUS), *args]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.stdout is None or process.stderr is None:  # pragma: no cover - subprocess contract
        process.kill()
        raise ProofExecutionError("incus_output_pipe_missing")
    streams = selectors.DefaultSelector()
    streams.register(process.stdout, selectors.EVENT_READ, "stdout")
    streams.register(process.stderr, selectors.EVENT_READ, "stderr")
    chunks: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    total = 0
    deadline = time.monotonic() + timeout
    try:
        while streams.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(command, timeout)
            for key, _ in streams.select(min(remaining, 0.2)):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    streams.unregister(key.fileobj)
                    continue
                total += len(chunk)
                if total > MAX_HOST_OUTPUT_BYTES:
                    process.kill()
                    process.wait()
                    raise ProofExecutionError("incus_output_limit_exceeded")
                chunks[key.data].append(chunk)
        return subprocess.CompletedProcess(
            command,
            process.wait(),
            b"".join(chunks["stdout"]).decode(errors="replace"),
            b"".join(chunks["stderr"]).decode(errors="replace"),
        )
    finally:
        streams.close()
        if process.poll() is None:
            process.kill()
            process.wait()


def checked_incus(*args: str, timeout: float = 120.0) -> str:
    result = run_incus(*args, timeout=timeout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-1000:]
        raise ProofExecutionError(f"incus_failed:{args[0]}:{detail}")
    return result.stdout


def guest_command(*command: str) -> tuple[str, ...]:
    environment = allowed_guest_environment()
    return ("/usr/bin/env", "-i", *(f"{key}={environment[key]}" for key in sorted(environment)), *command)


def _job(resource_id: str, operation: str, payload: dict[str, object]) -> VerifiedJob:
    return VerifiedJob(
        job_id=f"proof-{operation}", node_id="game-proof-node", resource_kind="vm", resource_id=resource_id,
        operation=operation, generation=1, payload=payload, idempotency_key=f"proof:{resource_id}:{operation}",
        lease_id="proof-lease", lease_until="2099-01-01T00:00:00Z",
    )


def execute_vm(resource_id: str, operation: str, payload: dict[str, object]) -> dict[str, object]:
    return asyncio.run(incus.execute(_job(resource_id, operation, payload)))


def require_capabilities(config: ProofConfig, fixture: Path) -> None:
    if not INCUS.is_file():
        raise ProofConfigurationError("incus_unavailable")
    if not KVM.exists() or not os.access(KVM, os.R_OK | os.W_OK):
        raise ProofConfigurationError("kvm_unavailable")
    if not config.godot_binary.is_file() or not os.access(config.godot_binary, os.X_OK):
        raise ProofConfigurationError("godot_unavailable")
    if hashlib.sha256(config.godot_binary.read_bytes()).hexdigest() != config.godot_sha256:
        raise ProofConfigurationError("godot_sha256_mismatch")
    if not fixture.is_dir() or {item.name for item in fixture.iterdir()} != FIXTURE_NAMES:
        raise ProofConfigurationError("fixture_invalid")
    version = run_incus("version", timeout=20.0)
    if version.returncode != 0 or "unreachable" in (version.stdout + version.stderr).lower():
        raise ProofConfigurationError("incus_unreachable")


def wait_for_agent(name: str, timeout: float = 180.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if run_incus("exec", name, "--", "/bin/true", timeout=15.0).returncode == 0:
            return
        time.sleep(2)
    raise ProofExecutionError("guest_agent_timeout")


def push_inputs(name: str, config: ProofConfig, fixture: Path) -> None:
    checked_incus("exec", name, "--", "mkdir", "-p", "/opt/game", "/opt/output")
    checked_incus(
        "exec", name, "--", "mount", "-t", "tmpfs", "-o",
        f"size={config.output_bytes},nr_inodes={config.output_inodes},nodev,nosuid,noexec", "tmpfs", "/opt/output",
    )
    checked_incus("file", "push", str(config.godot_binary), f"{name}/usr/local/bin/godot")
    checked_incus("exec", name, "--", "chmod", "0755", "/usr/local/bin/godot")
    for item in sorted(fixture.iterdir()):
        checked_incus("file", "push", str(item), f"{name}/opt/game/{item.name}")


def _probe_returncode(name: str, *command: str, timeout: float = 20.0) -> int:
    return run_incus("exec", name, "--", *guest_command(*command), timeout=timeout).returncode


def inspect_isolation(name: str, config: ProofConfig, host_sentinel: Path) -> dict[str, object]:
    instance = json.loads(checked_incus("list", name, "--format=json"))[0]
    devices = instance.get("expanded_devices", {})
    settings = instance.get("expanded_config", {})
    if not isinstance(settings, dict):
        raise ProofExecutionError("instance_config_invalid")
    if settings.get("volatile.base_image") != config.image_fingerprint:
        raise ProofExecutionError("image_fingerprint_mismatch")
    if settings.get("image.game-proof.godot-sha256") != config.godot_sha256:
        raise ProofExecutionError("image_godot_sha256_mismatch")
    for key in ("image.game-proof.source-image", "image.game-proof.packages-sha256"):
        if not isinstance(settings.get(key), str) or len(settings[key]) != 64:
            raise ProofExecutionError("image_provenance_missing")
    root = devices.get("root", {}) if isinstance(devices, dict) else {}
    network = devices.get("eth0", {}) if isinstance(devices, dict) else {}
    if network.get("type") != "none":
        raise ProofExecutionError("network_not_isolated")
    if instance.get("type") != "virtual-machine":
        raise ProofExecutionError("shared_kernel_not_allowed")
    interfaces = sorted(filter(None, checked_incus(
        "exec", name, "--", "/bin/sh", "-c", "for p in /sys/class/net/*; do basename \"$p\"; done",
    ).splitlines()))
    routes = [line for line in checked_incus(
        "exec", name, "--", *guest_command("/usr/sbin/ip", "route", "show"),
    ).splitlines() if line]
    guest_env = dict(line.split("=", 1) for line in checked_incus(
        "exec", name, "--", *guest_command("/usr/bin/env"),
    ).splitlines())
    secret_visible = _probe_returncode(name, "/usr/bin/printenv", "HH_GAME_PROOF_SECRET") == 0
    secret_visible |= _probe_returncode(name, "/usr/bin/test", "-e", str(host_sentinel)) == 0
    sockets_visible = _probe_returncode(
        name, "/bin/sh", "-c", "test -S /var/run/docker.sock -o -S /var/lib/incus/unix.socket -o -S /run/incus/unix.socket",
    ) == 0
    mount_targets = set(checked_incus(
        "exec", name, "--", *guest_command("/usr/bin/findmnt", "-rn", "-o", "TARGET"),
    ).splitlines())
    sensitive = {"/etc/hydrahive2", "/root/.ssh", "/home/till/.ssh", "/var/lib/incus", "/run/docker"}
    return {
        "virtualization": checked_incus("exec", name, "--", *guest_command("/usr/bin/systemd-detect-virt")).strip(),
        "guest_kernel": checked_incus("exec", name, "--", *guest_command("/usr/bin/uname", "-r")).strip(),
        "network_interfaces": interfaces,
        "default_routes": routes,
        "dns_available": _probe_returncode(name, "/usr/bin/getent", "ahosts", "example.com", timeout=5.0) == 0,
        "metadata_route_available": _probe_returncode(name, "/usr/sbin/ip", "route", "get", "169.254.169.254") == 0,
        "host_secret_visible": secret_visible,
        "host_mounts_visible": bool(mount_targets & sensitive),
        "host_sockets_visible": sockets_visible,
        "host_devices": forbidden_host_devices(devices if isinstance(devices, dict) else {}),
        "guest_environment": guest_env,
        "godot_sha256": config.godot_sha256,
        "godot_version": checked_incus(
            "exec", name, "--", *guest_command("/usr/local/bin/godot", "--version"),
        ).strip(),
        "image_fingerprint": settings.get("volatile.base_image"),
        "source_image_fingerprint": settings.get("image.game-proof.source-image"),
        "package_manifest_sha256": settings.get("image.game-proof.packages-sha256"),
        "output_mount_options": checked_incus(
            "exec", name, "--", *guest_command("/usr/bin/findmnt", "-n", "-o", "OPTIONS", "/opt/output"),
        ).strip(),
        "limits": {
            "cpu": settings.get("limits.cpu"), "memory": settings.get("limits.memory"), "disk": root.get("size"),
            "tasks_max": config.tasks_max, "output_bytes": config.output_bytes,
            "output_inodes": config.output_inodes, "max_files": config.max_files,
            "runtime_seconds": config.runtime_seconds,
        },
    }
