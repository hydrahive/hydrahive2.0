from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from game_microvm_harness import (
    ProofConfigurationError,
    ProofConfig,
    allowed_guest_environment,
    forbidden_host_devices,
    policy_digest,
    run_proof,
    vm_payload,
)

FIXTURE = Path(__file__).parent / "fixtures" / "game_runtime_godot"
FINGERPRINT = "a" * 64
GODOT_SHA256 = "b" * 64


def _env(**overrides: str) -> dict[str, str]:
    return {
        "HH_GAME_MICROVM_TEST": "1",
        "HH_GAME_MICROVM_FINGERPRINT": FINGERPRINT,
        "HH_GAME_GODOT_SHA256": GODOT_SHA256,
        **overrides,
    }


def test_proof_config_requires_explicit_opt_in() -> None:
    with pytest.raises(ProofConfigurationError, match="opt_in_required"):
        ProofConfig.from_env({})


@pytest.mark.parametrize("image", ["--vm", " images:ubuntu/24.04", "images:ubuntu/24.04\n--vm", "x" * 201])
def test_proof_config_rejects_unsafe_image(image: str) -> None:
    with pytest.raises(ProofConfigurationError, match="image_invalid"):
        ProofConfig.from_env({"HH_GAME_MICROVM_TEST": "1", "HH_GAME_MICROVM_IMAGE": image})


@pytest.mark.parametrize(
    "missing,code",
    [("HH_GAME_MICROVM_FINGERPRINT", "image_fingerprint_invalid"), ("HH_GAME_GODOT_SHA256", "godot_sha256_invalid")],
)
def test_proof_config_requires_image_and_godot_digests(missing: str, code: str) -> None:
    environ = _env()
    environ.pop(missing)
    with pytest.raises(ProofConfigurationError, match=code):
        ProofConfig.from_env(environ)


def test_vm_payload_is_fixed_and_bounded() -> None:
    config = ProofConfig.from_env(_env(HH_GAME_MICROVM_IMAGE="images:ubuntu/24.04/cloud"))

    assert vm_payload("hh-game-proof-abc123", config) == {
        "name": "hh-game-proof-abc123",
        "image": "images:ubuntu/24.04/cloud",
        "network_mode": "isolated",
        "cpu": 2,
        "ram_mb": 2048,
        "disk_gb": 10,
    }


@pytest.mark.parametrize("device_type", ["gpu", "usb", "pci", "proxy", "unix-char", "unix-block"])
def test_forbidden_host_device_types_are_detected(device_type: str) -> None:
    devices = {
        "root": {"type": "disk", "path": "/", "pool": "default", "size": "10GiB"},
        "eth0": {"type": "none"},
        "danger": {"type": device_type},
    }
    assert forbidden_host_devices(devices) == ["danger"]


def test_extra_host_disk_is_forbidden() -> None:
    devices = {
        "root": {"type": "disk", "path": "/", "pool": "default", "size": "10GiB"},
        "host": {"type": "disk", "source": "/home", "path": "/host"},
    }
    assert forbidden_host_devices(devices) == ["host"]


def test_guest_environment_is_a_small_positive_list() -> None:
    assert allowed_guest_environment() == {
        "HOME": "/root",
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "USER": "root",
    }


def test_policy_digest_is_stable_and_binds_image() -> None:
    first = ProofConfig.from_env(_env(HH_GAME_MICROVM_IMAGE="images:ubuntu/24.04/cloud"))
    second = ProofConfig.from_env(_env(HH_GAME_MICROVM_FINGERPRINT="c" * 64, HH_GAME_MICROVM_IMAGE="images:debian/12/cloud"))
    assert policy_digest(first) == policy_digest(first)
    assert policy_digest(first).startswith("sha256:")
    assert policy_digest(first) != policy_digest(second)


def test_host_output_is_bounded(monkeypatch, tmp_path: Path) -> None:
    import game_microvm_runtime as runtime

    executable = tmp_path / "noisy-incus"
    executable.write_text("#!/usr/bin/python3\nimport sys\nsys.stdout.write('x' * 300000)\n", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setattr(runtime, "INCUS", executable)
    with pytest.raises(runtime.ProofExecutionError, match="output_limit_exceeded"):
        runtime.run_incus("version")


def test_godot_fixture_is_minimal_and_versioned() -> None:
    assert {path.name for path in FIXTURE.iterdir()} == {
        "export_presets.cfg",
        "main.gd",
        "main.tscn",
        "project.godot",
    }
    assert "run/main_scene" in (FIXTURE / "project.godot").read_text(encoding="utf-8")
    script = (FIXTURE / "main.gd").read_text(encoding="utf-8")
    assert "draw_circle" in script
    assert "save_png" not in script


def test_committed_real_proof_is_bound_to_source_and_artifacts() -> None:
    repository = Path(__file__).resolve().parents[2]
    evidence = repository / "docs" / "audit" / "evidence"
    result = json.loads((evidence / "game-studio-pr0-result.json").read_text(encoding="utf-8"))
    from game_microvm_harness import _source_digest

    assert result["proof_mode"] == "real-incus-kvm"
    assert result["cleanup_confirmed"] is True
    assert result["image_cleanup_confirmed"] is True
    assert result["source_digest"] == _source_digest(FIXTURE)
    for name, hash_key, size_key in (
        ("game-studio-pr0-proof.png", "screenshot_sha256", "screenshot_size_bytes"),
        ("game-studio-pr0-proof.pck", "pck_sha256", "pck_size_bytes"),
    ):
        artifact = evidence / name
        assert artifact.stat().st_size == result[size_key]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == result[hash_key]


@pytest.mark.skipif(
    os.environ.get("HH_GAME_MICROVM_TEST") != "1",
    reason="echter KVM-/Incus-Nachweis nur mit HH_GAME_MICROVM_TEST=1",
)
def test_godot_runs_only_inside_fresh_linux_microvm(tmp_path: Path) -> None:
    result = run_proof(ProofConfig.from_env(os.environ), FIXTURE, tmp_path)

    assert result["runtime"] == "incus-vm"
    assert result["virtualization"] in {"kvm", "qemu"}
    assert result["guest_kernel"]
    assert result["network_interfaces"] == ["lo"]
    assert result["default_routes"] == []
    assert result["dns_available"] is False
    assert result["metadata_route_available"] is False
    assert result["host_secret_visible"] is False
    assert result["host_mounts_visible"] is False
    assert result["host_sockets_visible"] is False
    assert result["host_devices"] == []
    assert result["guest_environment"] == allowed_guest_environment()
    assert result["limits"] == {
        "cpu": "2", "memory": "2048MiB", "disk": "10GiB", "tasks_max": 256,
        "output_bytes": 64 * 1024 * 1024, "output_inodes": 128, "max_files": 128,
        "runtime_seconds": 180,
    }
    assert result["project_validated"] is True
    assert result["export_started"] is True
    assert result["cancel_tree_cleaned"] is True
    assert result["timeout_tree_cleaned"] is True
    assert result["image_fingerprint"]
    assert result["policy_digest"].startswith("sha256:")
    assert result["pck_sha256"]
    assert result["screenshot_sha256"]
    assert (tmp_path / "game-proof.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
