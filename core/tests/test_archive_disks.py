"""Etappe 1b: Platten zur Auswahl (Spec archiv-system.md, „Etappe 1b“).

Kein freies Pfadfeld – der Admin wählt eine Platte. Die Liste kommt aus mountinfo: nur echte, lokale, schreibbar
eingehängte Dateisysteme, jede Platte einmal, ohne Bind-Mounts, Netzlaufwerke, /boot, /home, /tmp, Projekt-Mounts.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.archive import disks

# Echter Auszug von Prod (13.10.2026), Spalte 4 = Wurzel im Dateisystem, nach „-“: Typ, Quelle, Optionen.
PROD = """\
1495 496 8:2 / / rw,relatime shared:787 master:1 - ext4 /dev/sda2 rw
2400 1495 8:1 / /boot/efi rw,relatime shared:1419 master:125 - vfat /dev/sda1 rw,fmask=0022
2401 1495 9:127 / /srv/fast rw,noatime shared:1671 master:129 - ext4 /dev/md127 rw
2402 2401 8:2 /var/lib/hydrahive2.hdd/workspaces /srv/fast/hydrahive2/workspaces rw,relatime - ext4 /dev/sda2 rw
2403 1495 9:127 /hydrahive2 /var/lib/hydrahive2 rw,noatime shared:1687 master:129 - ext4 /dev/md127 rw
2404 2403 8:2 /var/lib/hydrahive2.hdd/workspaces /var/lib/hydrahive2/workspaces rw,relatime - ext4 /dev/sda2 rw
2405 1495 0:55 / /var/lib/lxcfs rw,nosuid,nodev,relatime - fuse.lxcfs lxcfs rw
2406 1495 0:56 / /var/lib/incus/shmounts rw,relatime - tmpfs tmpfs rw
2410 1495 8:2 /home /home ro,relatime shared:1694 master:1 - ext4 /dev/sda2 rw
2411 1495 8:2 /tmp /tmp rw,relatime - ext4 /dev/sda2 rw
2420 2404 0:90 / /var/lib/hydrahive2/workspaces/projects/x/mounts/NAS rw,relatime - cifs //nas/share rw
2421 1495 8:33 / /media/usb rw,relatime - ext4 /dev/sdc1 rw
2422 1495 8:49 / /mnt/ro-platte ro,relatime - ext4 /dev/sdd1 ro
2423 1495 8:65 / /mnt/daten\\040neu rw,relatime - xfs /dev/sde1 rw
"""


@pytest.fixture
def mi(tmp_path, monkeypatch) -> Path:
    p = tmp_path / "mountinfo"
    p.write_text(PROD)
    monkeypatch.setattr(disks, "MOUNTINFO", p)
    monkeypatch.setattr(disks, "_usage", lambda path: (1000, 400))
    monkeypatch.setattr(disks, "_writable", lambda path: str(path).startswith("/srv"))
    return p


def test_only_real_local_disks_once(mi) -> None:
    mounts = [d["mount"] for d in disks.list_disks()]
    assert mounts == ["/", "/media/usb", "/mnt/daten neu", "/srv/fast"]


def test_target_folder_per_disk(mi) -> None:
    by_mount = {d["mount"]: d for d in disks.list_disks()}
    assert by_mount["/"]["path"] == "/srv/hydrahive-archiv"
    assert by_mount["/srv/fast"]["path"] == "/srv/fast/hydrahive-archiv"
    assert by_mount["/mnt/daten neu"]["path"] == "/mnt/daten neu/hydrahive-archiv"


def test_entries_carry_size_free_writable_and_device(mi) -> None:
    d = {x["mount"]: x for x in disks.list_disks()}["/srv/fast"]
    assert d["size_bytes"] == 1000 and d["free_bytes"] == 400
    assert d["fstype"] == "ext4" and d["device"] == "/dev/md127"
    assert d["writable"] is True
    assert {x["mount"]: x for x in disks.list_disks()}["/media/usb"]["writable"] is False


def test_id_is_stable_and_not_a_path(mi) -> None:
    ids = [d["id"] for d in disks.list_disks()]
    assert len(set(ids)) == len(ids)
    assert all("/" not in i for i in ids)
    assert disks.list_disks() == disks.list_disks()


def test_find_by_id(mi) -> None:
    first = disks.list_disks()[3]
    assert disks.find(first["id"])["mount"] == first["mount"]
    assert disks.find("gibt-es-nicht") is None
    assert disks.find("../../etc") is None


def test_unreadable_mountinfo_gives_empty_list(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(disks, "MOUNTINFO", tmp_path / "fehlt")
    assert disks.list_disks() == []


def test_root_target_check_for_runner(mi) -> None:
    """Dieselbe Prüfung, die der Root-Runner nutzt: nur Einhängepunkte aus der Liste."""
    assert disks.allowed_mount("/srv/fast") is True
    assert disks.allowed_mount("/") is True
    for bad in ("/home", "/boot/efi", "/tmp", "/var/lib/hydrahive2/workspaces", "/etc", "/srv/fast/../../etc",
                "/var/lib/hydrahive2/workspaces/projects/x/mounts/NAS", "relativ", ""):
        assert disks.allowed_mount(bad) is False, bad


# Echter Auszug aus einem incus-Container (hydratest, 13.10.2026): „/“ ist selbst ein Bind-Mount aus dem Speicher-Pool
# des Hosts (Wurzel ≠ „/“). Viele HydraHive-Installationen laufen so – „/“ muss trotzdem angeboten werden.
CONTAINER = """\
1541 1454 8:2 /var/lib/incus/storage-pools/default/containers/hydratest/rootfs / rw,relatime shared:1271 master:1 - ext4 /dev/sda2 rw
1542 1541 0:115 / /dev rw,relatime shared:1272 - tmpfs none rw,size=492k
1574 1541 0:61 / /var/lib/lxcfs rw,nosuid,nodev,relatime shared:1307 master:441 - fuse.lxcfs lxcfs rw
1494 1541 8:2 /var/lib/incus/storage-pools/default/custom/default_vol /mnt/vol rw,relatime shared:2220 master:1 - ext4 /dev/sda2 rw
1600 1541 8:33 /daten /mnt/zweite rw,relatime - ext4 /dev/sdc1 rw
"""


def test_container_root_is_offered(mi) -> None:
    mi.write_text(CONTAINER)
    mounts = [d["mount"] for d in disks.list_disks()]
    assert mounts == ["/", "/mnt/zweite"], "gleiche Platte (8:2) nur einmal, über den kürzesten Einhängepunkt"


def test_same_device_counted_by_major_minor(mi) -> None:
    """Gezählt wird das Gerät (MAJ:MIN), wie im Root-Runner – nicht der Quell-Name."""
    mi.write_text(
        "1 0 8:2 / / rw - ext4 /dev/sda2 rw\n"
        "2 1 8:2 / /mnt/gleich rw - ext4 /dev/disk/by-uuid/abc rw\n"
        "3 1 8:3 / /mnt/anders rw - ext4 /dev/sda2 rw\n"
    )
    assert [d["mount"] for d in disks.list_disks()] == ["/", "/mnt/anders"]
