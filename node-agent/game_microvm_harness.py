"""Opt-in orchestrator for the Game Studio PR-0 VM proof."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from game_microvm_contract import (
    ProofConfig, ProofConfigurationError, allowed_guest_environment,
    forbidden_host_devices, policy_digest, vm_payload,
)
from game_microvm_runtime import (
    ProofExecutionError, checked_incus as _checked, execute_vm as _execute,
    guest_command as _guest_command, inspect_isolation as _inspect_isolation,
    push_inputs as _push_inputs, require_capabilities as _require_capabilities,
    run_incus as _run, wait_for_agent as _wait_for_agent,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_limited(name: str, unit: str, config: ProofConfig, *command: str) -> None:
    _checked(
        "exec", name, "--", "systemd-run", "--quiet", "--wait", "--pipe", "--collect",
        f"--unit={unit}", f"--property=TasksMax={config.tasks_max}",
        f"--property=RuntimeMaxSec={config.runtime_seconds}s", *command,
        timeout=float(config.runtime_seconds + config.teardown_timeout_seconds),
    )


def _run_godot(name: str, config: ProofConfig, output: Path) -> tuple[str, str, int, int]:
    godot = _guest_command(
        "/usr/bin/xvfb-run", "-a", "/usr/local/bin/godot", "--path", "/opt/game", "--audio-driver", "Dummy",
    )
    _run_limited(name, "hh-game-proof-validate", config, *godot, "--editor", "--quit")
    _run_limited(
        name, "hh-game-proof-export", config, *godot,
        "--export-pack", "Linux PCK", "/opt/output/game-proof.pck",
    )
    _run_limited(
        name, "hh-game-proof-run", config, *_guest_command(
            "/usr/bin/xvfb-run", "-a", "/usr/local/bin/godot", "--main-pack", "/opt/output/game-proof.pck",
            "--rendering-method", "gl_compatibility", "--audio-driver", "Dummy",
            "--write-movie", "/opt/output/game-proof.png", "--fixed-fps", "1", "--quit-after", "2",
        ),
    )
    output_files = _checked("exec", name, "--", *_guest_command(
        "/usr/bin/find", "/opt/output", "-xdev", "-type", "f",
    )).splitlines()
    if len(output_files) > config.max_files:
        raise ProofExecutionError("output_file_limit_exceeded")
    frames = sorted(path for path in output_files if path.endswith(".png"))
    if not frames:
        raise ProofExecutionError("godot_frame_missing")
    pck = output / "game-proof.pck"
    png = output / "game-proof.png"
    _checked("file", "pull", f"{name}/opt/output/game-proof.pck", str(pck))
    _checked("file", "pull", f"{name}{frames[0]}", str(png))
    if not pck.is_file() or pck.stat().st_size == 0 or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ProofExecutionError("godot_evidence_invalid")
    return _sha256(pck), _sha256(png), pck.stat().st_size, png.stat().st_size


def _prove_cancel(name: str, resource_id: str, config: ProofConfig) -> bool:
    unit = "hh-game-proof-cancel"
    _checked(
        "exec", name, "--", "systemd-run", f"--unit={unit}", f"--property=TasksMax={config.tasks_max}",
        "/bin/bash", "-c", f"exec -a {unit}-marker /bin/bash -c 'sleep 600 & wait'",
    )
    actual = _checked("exec", name, "--", "systemctl", "show", unit, "-p", "TasksMax", "--value").strip()
    if actual != str(config.tasks_max):
        raise ProofExecutionError("guest_pid_limit_missing")
    started = time.monotonic()
    _execute(resource_id, "vm.stop", {"name": name})
    if time.monotonic() - started > config.teardown_timeout_seconds:
        raise ProofExecutionError("cancel_deadline_exceeded")
    _execute(resource_id, "vm.start", {"name": name})
    _wait_for_agent(name)
    unit_gone = _run("exec", name, "--", "systemctl", "is-active", unit).returncode != 0
    process_gone = _run("exec", name, "--", "pgrep", "-f", f"{unit}-marker").returncode != 0
    return unit_gone and process_gone


def _prove_timeout(name: str, config: ProofConfig) -> bool:
    unit = "hh-game-proof-timeout"
    started = time.monotonic()
    result = _run(
        "exec", name, "--", "systemd-run", "--quiet", "--wait", "--pipe", "--collect",
        f"--unit={unit}", f"--property=TasksMax={config.tasks_max}", "--property=RuntimeMaxSec=2s",
        "/bin/bash", "-c", f"exec -a {unit}-marker /bin/bash -c 'sleep 600 & wait'",
        timeout=float(config.teardown_timeout_seconds),
    )
    elapsed = time.monotonic() - started
    if result.returncode == 0 or elapsed > config.teardown_timeout_seconds:
        raise ProofExecutionError("timeout_not_enforced")
    return _run("exec", name, "--", "pgrep", "-f", f"{unit}-marker").returncode != 0


def _host_versions() -> dict[str, str]:
    qemu = shutil.which("qemu-system-x86_64")
    qemu_version = "unavailable"
    if qemu:
        qemu_version = subprocess.run([qemu, "--version"], text=True, capture_output=True, check=False).stdout.splitlines()[0]
    return {
        "host_kernel": os.uname().release,
        "incus": _checked("version", timeout=20.0).strip().replace("\n", "; "),
        "qemu": qemu_version,
    }


def _source_digest(fixture: Path) -> str:
    root = Path(__file__).resolve().parent
    files = [
        root / "game_microvm_contract.py",
        root / "game_microvm_runtime.py",
        root / "game_microvm_harness.py",
        root / "src/hydrahive_node/incus.py",
        root / "tests/build_game_microvm_image.sh",
        root / "tests/run_game_microvm_proof.py",
        root / "tests/test_game_runtime_microvm_smoke.py",
        *sorted(fixture.iterdir()),
    ]
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _instance_exists(name: str) -> bool:
    result = _run("list", name, "--format=json", timeout=20.0)
    if result.returncode != 0:
        raise ProofExecutionError("cleanup_inspection_failed")
    try:
        rows = json.loads(result.stdout)
    except ValueError as exc:
        raise ProofExecutionError("cleanup_inspection_invalid") from exc
    return any(isinstance(row, dict) and row.get("name") == name for row in rows)


def _delete_vm(resource_id: str, name: str) -> None:
    for _ in range(3):
        try:
            _execute(resource_id, "vm.delete", {"name": name})
        except Exception:
            _run("delete", name, "--force", timeout=60.0)
        if not _instance_exists(name):
            return
        time.sleep(1)
    raise ProofExecutionError("vm_cleanup_failed")


def run_proof(config: ProofConfig, fixture: Path, output: Path) -> dict[str, object]:
    _require_capabilities(config, fixture)
    output.mkdir(parents=True, exist_ok=True)
    sentinel = output / "host-secret.txt"
    sentinel.write_text("must-not-enter-guest", encoding="utf-8")
    os.environ["HH_GAME_PROOF_SECRET"] = "must-not-enter-guest"
    resource_id = str(uuid.uuid4())
    name = f"hh-game-proof-{uuid.uuid4().hex[:6]}"
    source_digest = _source_digest(fixture)
    result: dict[str, object] | None = None
    try:
        if _instance_exists(name):
            raise ProofExecutionError("vm_name_collision")
        created = _execute(resource_id, "vm.create_from_image", vm_payload(name, config))
        if created.get("actual_state") != "running":
            raise ProofExecutionError("vm_not_running")
        _wait_for_agent(name)
        _push_inputs(name, config, fixture)
        isolation = _inspect_isolation(name, config, sentinel)
        failed_checks = [key for key in (
            "host_devices", "host_secret_visible", "host_mounts_visible", "host_sockets_visible",
            "default_routes", "dns_available", "metadata_route_available",
        ) if isolation[key]]
        if isolation["network_interfaces"] != ["lo"]:
            failed_checks.append("network_interfaces")
        if isolation["guest_environment"] != allowed_guest_environment():
            failed_checks.append("guest_environment")
        if failed_checks:
            raise ProofExecutionError(f"guest_isolation_failed:{','.join(failed_checks)}")
        pck_hash, png_hash, pck_size, png_size = _run_godot(name, config, output)
        cancel_cleaned = _prove_cancel(name, resource_id, config)
        timeout_cleaned = _prove_timeout(name, config)
        if not cancel_cleaned or not timeout_cleaned:
            raise ProofExecutionError("process_tree_survived")
        result = {
            "proof_mode": "real-incus-kvm",
            "executed_at": datetime.now(UTC).isoformat(),
            "source_digest": source_digest,
            "runtime": "incus-vm",
            **_host_versions(),
            **isolation,
            "policy_digest": policy_digest(config),
            "project_validated": True,
            "export_started": True,
            "cancel_tree_cleaned": True,
            "timeout_tree_cleaned": True,
            "pck_sha256": pck_hash,
            "pck_size_bytes": pck_size,
            "screenshot_sha256": png_hash,
            "screenshot_size_bytes": png_size,
        }
    finally:
        try:
            _delete_vm(resource_id, name)
        finally:
            os.environ.pop("HH_GAME_PROOF_SECRET", None)
    if result is None:  # pragma: no cover - exception path never reaches here
        raise ProofExecutionError("proof_result_missing")
    result["cleanup_confirmed"] = True
    return result
