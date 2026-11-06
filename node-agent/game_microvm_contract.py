"""Pure, test-only policy contract for the Game Studio PR-0 VM proof."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
FORBIDDEN_DEVICE_TYPES = {"gpu", "usb", "pci", "proxy", "unix-char", "unix-block"}


class ProofConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProofConfig:
    image: str
    image_fingerprint: str
    godot_binary: Path
    godot_sha256: str
    cpu: int = 2
    ram_mb: int = 2048
    disk_gb: int = 10
    tasks_max: int = 256
    output_bytes: int = 64 * 1024 * 1024
    output_inodes: int = 128
    max_files: int = 128
    runtime_seconds: int = 180
    teardown_timeout_seconds: int = 30

    @classmethod
    def from_env(cls, environ: os._Environ[str] | dict[str, str]) -> "ProofConfig":
        if environ.get("HH_GAME_MICROVM_TEST") != "1":
            raise ProofConfigurationError("opt_in_required")
        image = environ.get("HH_GAME_MICROVM_IMAGE", "images:ubuntu/24.04/cloud")
        if IMAGE_RE.fullmatch(image) is None:
            raise ProofConfigurationError("image_invalid")
        binary = Path(environ.get("HH_GAME_GODOT_BINARY", "/usr/local/bin/godot"))
        if not binary.is_absolute():
            raise ProofConfigurationError("godot_path_invalid")
        fingerprint = environ.get("HH_GAME_MICROVM_FINGERPRINT", "")
        godot_sha256 = environ.get("HH_GAME_GODOT_SHA256", "")
        if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
            raise ProofConfigurationError("image_fingerprint_invalid")
        if re.fullmatch(r"[0-9a-f]{64}", godot_sha256) is None:
            raise ProofConfigurationError("godot_sha256_invalid")
        return cls(image=image, image_fingerprint=fingerprint, godot_binary=binary, godot_sha256=godot_sha256)


def vm_payload(name: str, config: ProofConfig) -> dict[str, object]:
    if re.fullmatch(r"hh-game-proof-[0-9a-f]{6}", name) is None:
        raise ProofConfigurationError("vm_name_invalid")
    return {
        "name": name,
        "image": config.image,
        "network_mode": "isolated",
        "cpu": config.cpu,
        "ram_mb": config.ram_mb,
        "disk_gb": config.disk_gb,
    }


def allowed_guest_environment() -> dict[str, str]:
    return {
        "HOME": "/root",
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "USER": "root",
    }


def policy_digest(config: ProofConfig) -> str:
    policy = {
        "runtime": "incus-vm",
        "image_fingerprint": config.image_fingerprint,
        "godot_sha256": config.godot_sha256,
        "network": "off",
        "host_devices": False,
        "limits": {
            "cpu": config.cpu,
            "ram_mb": config.ram_mb,
            "disk_gb": config.disk_gb,
            "tasks_max": config.tasks_max,
            "output_bytes": config.output_bytes,
            "output_inodes": config.output_inodes,
            "max_files": config.max_files,
            "runtime_seconds": config.runtime_seconds,
        },
        "environment": allowed_guest_environment(),
    }
    encoded = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def forbidden_host_devices(devices: dict[str, object]) -> list[str]:
    forbidden: list[str] = []
    for name, raw in devices.items():
        device = raw if isinstance(raw, dict) else {}
        kind = device.get("type")
        if kind in FORBIDDEN_DEVICE_TYPES:
            forbidden.append(name)
        elif kind == "disk" and (name != "root" or device.get("path") != "/" or device.get("source")):
            forbidden.append(name)
        elif kind not in {"disk", "none"}:
            forbidden.append(name)
    return sorted(forbidden)
