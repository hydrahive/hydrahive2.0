"""Baut die argv-Liste für `qemu-system-x86_64` aus einer VM-Konfig.

Bewusst keine Shell-Strings — alles als Liste an subprocess.Popen, kein shell=True.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings
from hydrahive.vms.models import VM


def build_qemu_args(vm: VM, vnc_port: int) -> list[str]:
    """argv für qemu-system-x86_64 — VNC-Display = vnc_port - 5900."""
    iso_path = settings.vms_isos_dir / vm.iso_filename if vm.iso_filename else None
    pid_file = settings.vms_pids_dir / f"{vm.vm_id}.pid"
    qmp_socket = settings.vms_pids_dir / f"{vm.vm_id}.qmp"

    # KVM nur wenn /dev/kvm existiert. Bei TCG kein "-cpu max" — emuliert AES-NI/SHA-NI
    # buggy → FreeBSD libcrypto crash. qemu64 ist konservativ und stabil.
    has_kvm = Path("/dev/kvm").exists()
    cpu_model = "host" if has_kvm else "qemu64"
    machine = "q35,accel=kvm" if has_kvm else "q35,accel=tcg"

    args: list[str] = [
        "qemu-system-x86_64",
        "-name", f"hh2-{vm.name}",
        "-machine", machine,
        "-cpu", cpu_model,
        "-smp", str(vm.cpu),
        "-m", str(vm.ram_mb),
        "-drive", f"file={vm.qcow2_path},format=qcow2,if=virtio,cache=writeback,discard=unmap",
        "-pidfile", str(pid_file),
        "-qmp", f"unix:{qmp_socket},server=on,wait=off",
        "-display", f"vnc=127.0.0.1:{vnc_port - 5900}",
        "-rtc", "base=utc,clock=host",
        "-device", "virtio-balloon",
        "-device", "virtio-rng-pci",
        "-daemonize",
    ]

    # Boot-Reihenfolge: ISO > Disk wenn ISO vorhanden, sonst nur Disk
    if iso_path and iso_path.exists():
        args += [
            "-drive", f"file={iso_path},media=cdrom,readonly=on",
            "-boot", "order=dc,menu=on",  # d=cdrom, c=disk, mit Boot-Menü
        ]
    else:
        args += ["-boot", "order=c,menu=on"]

    # Networking
    if vm.network_mode == "bridged":
        args += [
            "-netdev", f"bridge,id=net0,br={settings.vms_bridge}",
            "-device", f"virtio-net-pci,netdev=net0,mac={_mac_for(vm.vm_id)}",
        ]
    elif vm.network_mode == "isolated":
        args += [
            "-netdev", "user,id=net0,restrict=yes",  # restrict=yes blockt Internet
            "-device", f"virtio-net-pci,netdev=net0,mac={_mac_for(vm.vm_id)}",
        ]

    return args


def _mac_for(vm_id: str) -> str:
    """Stabile MAC aus vm_id — locally-administered (52:54:00 ist QEMU-default)."""
    h = vm_id.replace("-", "")[:6]
    return f"52:54:00:{h[0:2]}:{h[2:4]}:{h[4:6]}"


def ensure_dirs() -> None:
    """Anlegen der VM-Verzeichnisse — idempotent, beim ersten Backend-Start."""
    for d in (settings.vms_dir, settings.vms_isos_dir, settings.vms_disks_dir,
              settings.vms_pids_dir, settings.vms_logs_dir, settings.vms_vnc_tokens_dir):
        d.mkdir(parents=True, exist_ok=True)


def qcow2_create_args(target: Path, size_gb: int) -> list[str]:
    """argv für qemu-img create."""
    return ["qemu-img", "create", "-f", "qcow2", str(target), f"{size_gb}G"]
