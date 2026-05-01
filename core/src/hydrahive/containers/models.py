"""Container-Datentypen."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DesiredState = Literal["running", "stopped"]
ActualState = Literal["created", "starting", "running", "stopping", "stopped", "error"]
NetworkMode = Literal["bridged", "isolated"]


@dataclass
class Container:
    container_id: str
    owner: str
    name: str
    image: str
    network_mode: NetworkMode
    desired_state: DesiredState
    actual_state: ActualState
    created_at: str
    updated_at: str
    description: str | None = None
    cpu: int | None = None
    ram_mb: int | None = None
    last_error_code: str | None = None
    last_error_params: dict | None = None
    project_id: str | None = None


@dataclass
class ContainerImage:
    alias: str           # z.B. "debian/12"
    fingerprint: str
    description: str
    architecture: str
    size_bytes: int


# Limits + Validation
NAME_RE = r"^[a-zA-Z][a-zA-Z0-9-]{0,62}$"  # incus erlaubt bis 63 chars
MIN_CPU = 1
MAX_CPU = 16
MIN_RAM_MB = 64
MAX_RAM_MB = 32768

# Curated Quick-Pick für UI — nicht ausschließend, User kann custom alias eingeben
QUICK_IMAGES = [
    "debian/12",
    "debian/13",
    "ubuntu/24.04",
    "ubuntu/22.04",
    "alpine/3.21",
    "archlinux",
    "centos/9-Stream",
]
