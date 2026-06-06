"""Baut die argv-Liste für `qemu-system-x86_64` aus einer VM-Konfig.

Bewusst keine Shell-Strings — alles als Liste an subprocess.Popen, kein shell=True.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings
from hydrahive.vms.models import PassthroughDisk, VM


def _iso_drive_path(vm: VM) -> Path | None:
    """ISO-Pfad nur zurückgeben, wenn er real existiert UND unter vms_isos_dir
    liegt. Defense-in-Depth gegen Path-Traversal in vm.iso_filename (Issue #179):
    selbst wenn ein roher '../../etc/passwd'-Wert in die DB gelangt, wird hier
    keine Datei außerhalb der ISO-Library als -drive gemountet."""
    if not vm.iso_filename:
        return None
    isos_dir = settings.vms_isos_dir.resolve()
    iso_path = (settings.vms_isos_dir / vm.iso_filename).resolve()
    if not iso_path.is_file() or not iso_path.is_relative_to(isos_dir):
        return None
    return iso_path


def build_qemu_args(vm: VM, vnc_port: int,
                    passthrough_disks: list[PassthroughDisk] | None = None) -> list[str]:
    """argv für qemu-system-x86_64 — VNC-Display = vnc_port - 5900."""
    iso_path = _iso_drive_path(vm)
    pid_file = settings.vms_pids_dir / f"{vm.vm_id}.pid"
    qmp_socket = settings.vms_pids_dir / f"{vm.vm_id}.qmp"

    # KVM nur wenn /dev/kvm existiert. Bei TCG kein "-cpu max" — emuliert AES-NI/SHA-NI
    # buggy → FreeBSD libcrypto crash. qemu64 ist konservativ und stabil.
    has_kvm = Path("/dev/kvm").exists()
    cpu_model = "host" if has_kvm else "qemu64"
    # vm.machine_type ist 'q35' oder 'pc' — accel-Suffix abhängig von /dev/kvm.
    machine = f"{vm.machine_type},accel={'kvm' if has_kvm else 'tcg'}"

    args: list[str] = [
        "qemu-system-x86_64",
        "-name", f"hh2-{vm.name}",
        "-machine", machine,
        "-cpu", cpu_model,
        "-smp", str(vm.cpu),
        "-m", str(vm.ram_mb),
        "-pidfile", str(pid_file),
        "-qmp", f"unix:{qmp_socket},server=on,wait=off",
        "-display", f"vnc=127.0.0.1:{vnc_port - 5900}",
        "-rtc", "base=utc,clock=host",
        "-device", "virtio-balloon",
        "-device", "virtio-rng-pci",
        "-daemonize",
    ]
    args += _disk_args(vm)
    args += _passthrough_disk_args(passthrough_disks or [])

    # Boot-Reihenfolge: ISO > Disk wenn ISO vorhanden, sonst nur Disk
    if iso_path:
        args += [
            "-drive", f"file={iso_path},media=cdrom,readonly=on",
            "-boot", "order=dc,menu=on",  # d=cdrom, c=disk, mit Boot-Menü
        ]
    else:
        args += ["-boot", "order=c,menu=on"]

    # Networking — vm.network_device ist 'virtio-net-pci' oder 'e1000'.
    nic = vm.network_device
    if vm.network_mode == "bridged":
        args += [
            "-netdev", f"bridge,id=net0,br={settings.vms_bridge}",
            "-device", f"{nic},netdev=net0,mac={_mac_for(vm.vm_id)}",
        ]
    elif vm.network_mode == "isolated":
        args += [
            "-netdev", "user,id=net0,restrict=yes",  # restrict=yes blockt Internet
            "-device", f"{nic},netdev=net0,mac={_mac_for(vm.vm_id)}",
        ]

    return args


def _disk_args(vm: VM) -> list[str]:
    """Disk-Args je nach gewähltem Interface.

    virtio: Default, schnellste Performance — nur für Gäste mit virtio-Treibern
            (moderne Linux mit virtio-blk-Modul).
    sata:   AHCI/IDE-HD — für importierte Images aus VirtualBox/HH1/etc.
            wo der Bootloader keinen virtio-Treiber hat.
    ide:    klassisches IDE — Notnagel für sehr alte Images.
    """
    iface = vm.disk_interface
    if iface == "sata":
        return [
            "-drive", f"file={vm.qcow2_path},format=qcow2,if=none,id=disk0,"
                      "cache=writeback,discard=unmap",
            "-device", "ahci,id=ahci",
            "-device", "ide-hd,bus=ahci.0,drive=disk0",
        ]
    if iface == "ide":
        # discard=unmap absichtlich NICHT — IDE hat kein TRIM, und in einigen
        # FreeBSD-Boot-Loadern (gptzfsboot) führt das bei IRQ-Race zu I/O-Errors.
        return [
            "-drive", f"file={vm.qcow2_path},format=qcow2,if=ide,cache=writeback",
        ]
    # default: virtio
    return [
        "-drive", f"file={vm.qcow2_path},format=qcow2,if=virtio,"
                  "cache=writeback,discard=unmap",
    ]


def _passthrough_disk_args(disks: list[PassthroughDisk]) -> list[str]:
    """QEMU-Args für alle Passthrough-Disks der VM.

    Jede Disk bekommt ein eigenes virtio-blk-Gerät (if=none + device).
    format=raw weil Block-Devices kein qcow2-Overhead brauchen.
    cache=none + aio=native für direkten I/O ohne Kernel-Buffer-Dopplung.
    """
    args: list[str] = []
    for idx, disk in enumerate(disks):
        drive_id = f"ptdisk{idx}"
        args += [
            "-drive", f"file={disk.device_path},format=raw,if=none,id={drive_id},"
                      "cache=writeback,aio=threads",
            "-device", f"virtio-blk-pci,drive={drive_id}",
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
