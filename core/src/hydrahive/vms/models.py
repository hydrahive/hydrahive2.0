"""VM-Datentypen — Dataclasses für Persistenz und API-Antworten."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DesiredState = Literal["running", "stopped"]
ActualState = Literal["created", "starting", "running", "stopping", "stopped", "error"]
NetworkMode = Literal["bridged", "isolated"]
ImportStatus = Literal["queued", "running", "done", "failed"]
DiskInterface = Literal["virtio", "sata", "ide"]
DISK_INTERFACES: tuple[str, ...] = ("virtio", "sata", "ide")
MachineType = Literal["q35", "pc"]
MACHINE_TYPES: tuple[str, ...] = ("q35", "pc")
NetworkDevice = Literal["virtio-net-pci", "e1000"]
NETWORK_DEVICES: tuple[str, ...] = ("virtio-net-pci", "e1000")
VMRuntime = Literal["qemu", "incus"]


@dataclass
class VM:
    vm_id: str
    owner: str
    name: str
    cpu: int
    ram_mb: int
    disk_gb: int
    qcow2_path: str
    network_mode: NetworkMode
    desired_state: DesiredState
    actual_state: ActualState
    created_at: str
    updated_at: str
    disk_interface: DiskInterface = "virtio"
    machine_type: MachineType = "q35"
    network_device: NetworkDevice = "virtio-net-pci"
    description: str | None = None
    iso_filename: str | None = None
    pid: int | None = None
    vnc_port: int | None = None
    vnc_token: str | None = None
    last_error_code: str | None = None
    last_error_params: dict | None = None
    project_id: str | None = None
    node_id: str = "local"
    generation: int = 0
    runtime: VMRuntime = "qemu"
    runtime_ref: str | None = None
    image: str | None = None


@dataclass
class ISO:
    filename: str
    size_bytes: int
    sha256: str
    uploaded_at: str


@dataclass
class Snapshot:
    snapshot_id: str
    vm_id: str
    name: str
    created_at: str
    description: str | None = None
    size_bytes: int | None = None


@dataclass
class PassthroughDisk:
    passthrough_id: str
    vm_id: str
    device_path: str
    label: str | None
    added_at: str


@dataclass
class HostDisk:
    """Block-Device auf dem Host — von lsblk geliefert."""
    name: str
    path: str
    size: str
    model: str | None
    serial: str | None
    children: list["HostDisk"]


@dataclass
class ImportJob:
    job_id: str
    owner: str
    source_path: str
    target_qcow2: str
    status: ImportStatus
    created_at: str
    progress_pct: int = 0
    bytes_done: int = 0
    bytes_total: int = 0
    error_code: str | None = None
    finished_at: str | None = None


# Limits — werden in der API gegen User-Eingaben validiert
MIN_CPU = 1
MAX_CPU = 16
MIN_RAM_MB = 256
MAX_RAM_MB = 65536
MIN_DISK_GB = 1
MAX_DISK_GB = 1024
NAME_RE = r"^[a-zA-Z][a-zA-Z0-9-]{0,31}$"  # 1-32 chars, alphanumeric+dash

# Image reference for image-based remote (Incus) VMs. Same shape as the
# container image allowlist regex; ISO/import paths are not accepted here.
IMAGE_RE = r"^(?:[a-zA-Z0-9][a-zA-Z0-9-]*:)?[a-zA-Z0-9][a-zA-Z0-9._/-]*$"

# Curated images offered for remote image VMs. Agent nodes only launch VM-capable
# cloud images; ISO installs and imports stay a local-only workflow.
VM_QUICK_IMAGES = [
    "images:debian/12",
    "images:ubuntu/24.04",
    "images:ubuntu/22.04",
    "images:fedora/40",
    "images:archlinux",
]
