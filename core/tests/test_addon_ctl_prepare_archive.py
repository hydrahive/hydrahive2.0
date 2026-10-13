"""Etappe 1b: Root-Runner richtet eine Platte für das Archiv ein (installer/addon-ctl.sh, „prepare-archive <id>“).

Aus der Oberfläche kommt nur eine 12-stellige ID. Der Runner baut seine eigene Platten-Liste (findmnt) mit denselben
Regeln wie archive/disks.py, sucht die ID darin und legt nur <einhängepunkt>/hydrahive-archiv an. Kein Pfad aus der
Anfrage erreicht die Shell.
"""
from __future__ import annotations

import hashlib
import os
import pwd
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
CTL = INSTALLER / "addon-ctl.sh"


def _id(mount: str) -> str:
    return hashlib.sha256(mount.encode()).hexdigest()[:12]


def _exe(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def box(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    (repo / "installer" / "lib").mkdir(parents=True)
    (repo / "installer" / "modules").mkdir()
    for lib in ("install-choices.sh", "archive-disk.sh"):
        src = INSTALLER / "lib" / lib
        if src.exists():
            shutil.copy(src, repo / "installer" / "lib")
    data, conf, bin_dir = tmp_path / "data", tmp_path / "etc", tmp_path / "bin"
    for d in (data, conf, bin_dir):
        d.mkdir()
    platte = tmp_path / "platte mit leer"
    platte.mkdir()
    ro = tmp_path / "ro"
    ro.mkdir()
    esc = str(platte).replace(" ", "\\x20")
    _exe(bin_dir / "findmnt", f"""#!/bin/sh
cat <<'EOF'
/ / ext4 rw,relatime 8:2
/boot/efi / vfat rw,relatime 8:1
{esc} / ext4 rw,relatime 8:33
{ro} / ext4 ro,relatime 8:49
{data}/workspaces /var/lib/x ext4 rw,relatime 8:2
{tmp_path}/nas / cifs rw,relatime 0:90
EOF
""")
    return {"repo": repo, "data": data, "conf": conf, "bin": bin_dir, "platte": platte, "ro": ro,
            "trigger": data / ".addon_request", "tmp": tmp_path}


def _run(box: dict, request: str) -> subprocess.CompletedProcess[str]:
    box["trigger"].write_text(request)
    me = pwd.getpwuid(os.getuid()).pw_name
    env = {"PATH": f"{box['bin']}:/usr/bin:/bin", "HH_REPO_DIR": str(box["repo"]), "HH_DATA_DIR": str(box["data"]),
           "HH_CONFIG_DIR": str(box["conf"]), "HH_USER": me,
           # Test-„Platten“ liegen unter /tmp (pytest) – Sperrliste ohne /tmp, sonst die echte.
           "HH_ARCHIVE_DISK_BLOCKED": "/boot /home /root /var/tmp /proc /sys /dev /run /etc /usr"}
    shutil.copy(CTL, box["repo"] / "installer" / "addon-ctl.sh")
    return subprocess.run(["bash", str(box["repo"] / "installer" / "addon-ctl.sh")], env=env,
                          capture_output=True, text=True, timeout=30)


def test_prepares_listed_disk(box) -> None:
    r = _run(box, f"prepare-archive {_id(str(box['platte']))}\n")
    assert r.returncode == 0, r.stdout + r.stderr
    target = box["platte"] / "hydrahive-archiv"
    assert target.is_dir() and not target.is_symlink()
    assert stat.S_IMODE(target.stat().st_mode) == 0o2775
    assert target.stat().st_uid == os.getuid()
    assert "[hh2-addon] FERTIG: prepare-archive" in r.stdout
    assert not box["trigger"].exists()


@pytest.mark.parametrize("which", ["ro", "boot", "bind", "nas", "unknown"])
def test_refuses_disks_outside_the_rules(box, which) -> None:
    mount = {"ro": str(box["ro"]), "boot": "/boot/efi", "bind": f"{box['data']}/workspaces",
             "nas": f"{box['tmp']}/nas", "unknown": "/gibt/es/nicht"}[which]
    r = _run(box, f"prepare-archive {_id(mount)}\n")
    assert r.returncode != 0
    assert "[hh2-addon] FEHLER" in r.stdout
    assert not (Path(mount) / "hydrahive-archiv").exists()


def test_refuses_symlinked_target(box) -> None:
    elsewhere = box["tmp"] / "anderswo"
    elsewhere.mkdir()
    (box["platte"] / "hydrahive-archiv").symlink_to(elsewhere)
    os.chmod(elsewhere, 0o700)
    mode_before = stat.S_IMODE(elsewhere.stat().st_mode)
    r = _run(box, f"prepare-archive {_id(str(box['platte']))}\n")
    assert r.returncode != 0
    assert stat.S_IMODE(elsewhere.stat().st_mode) == mode_before, "Symlink-Ziel darf nicht angefasst werden"
    assert "Symlink" in r.stdout


@pytest.mark.parametrize("request_text", [
    "prepare-archive", "prepare-archive /etc", "prepare-archive ../../etc", "prepare-archive ABCDEF012345",
    "prepare-archive 0123456789abc", "prepare-archive 0123456789a", "prepare-archive 0123456789ab; rm -rf /",
])
def test_only_twelve_hex_digits(box, request_text) -> None:
    r = _run(box, request_text)
    assert r.returncode == 2
    assert "unbekannte Anfrage verworfen" in r.stdout


def test_same_id_as_python(box, monkeypatch) -> None:
    """Python (archive/disks.py) und Runner rechnen dieselbe ID."""
    from hydrahive.archive import disks
    assert disks.disk_id(str(box["platte"])) == _id(str(box["platte"]))


def test_blocklist_same_as_python() -> None:
    """Die Sperrliste im Runner muss zu archive/disks.py passen."""
    from hydrahive.archive import disks
    text = (INSTALLER / "lib" / "archive-disk.sh").read_text()
    line = next(x for x in text.splitlines() if x.startswith("HH_ARCHIVE_DISK_BLOCKED_DEFAULT="))
    assert tuple(line.split("=", 1)[1].strip('"').split()) == disks.BLOCKED


def test_container_root_is_allowed(box) -> None:
    """Wie in Python: „/“ in einem Container (Wurzel ≠ „/“) ist erlaubt → Ziel /srv/hydrahive-archiv.
    Hier nur die Liste prüfen – /srv im Test nicht anfassen."""
    _exe(box["bin"] / "findmnt", "#!/bin/sh\necho '/ /var/lib/incus/storage-pools/x/rootfs ext4 rw,relatime 8:2'\n")
    lib = INSTALLER / "lib" / "archive-disk.sh"
    out = subprocess.run(["bash", "-c", f"source '{lib}'; hh_archive_disk_list"], capture_output=True, text=True,
                         env={"PATH": f"{box['bin']}:/usr/bin:/bin", "HH_DATA_DIR": str(box["data"])}, timeout=30)
    assert out.stdout.strip() == f"{_id('/')}\t/"
