"""lsblk unter dem AppArmor-Profil von Ubuntu 26.04 (Befund 23.11.2026, Neuinstallation).

/etc/apparmor.d/lsblk erlaubt als Ausgabe nur Terminal, /dev/null und Pipes – nicht Sockets und nicht Dateien.
Der Dienst läuft unter uvloop; dessen create_subprocess_exec hängt stdout an ein socketpair → lsblk schreibt still
nichts, /api/vms/host-disks meldete „lsblk_parse_error“. Die Attrappe unten benimmt sich genau so: Ist ihre Ausgabe
ein Socket, schreibt sie nichts (Exit 0) – wie das echte Profil.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from hydrahive.vms import _lsblk
from hydrahive.vms import passthrough as pt

uvloop = pytest.importorskip("uvloop")

DATA = {"blockdevices": [
    {"name": "sda", "path": "/dev/sda", "size": "1T", "type": "disk", "mountpoint": None, "model": "X",
     "serial": "S1", "children": []},
    {"name": "loop0", "path": "/dev/loop0", "size": "1M", "type": "loop", "mountpoint": None, "model": None,
     "serial": None},
]}


@pytest.fixture
def apparmor_lsblk(tmp_path, monkeypatch):
    """lsblk-Attrappe: schreibt nur, wenn stdout KEIN Socket ist (wie /etc/apparmor.d/lsblk auf 26.04)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "data.json").write_text(json.dumps(DATA))
    script = bin_dir / "lsblk"
    script.write_text(f"""#!/bin/bash
echo "$*" >> "{tmp_path}/calls"
[ -S /dev/stdout ] && exit 0
cat "{tmp_path}/data.json"
""")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    return tmp_path


def test_attrappe_gibt_unter_uvloop_alter_art_nichts(apparmor_lsblk):
    """Gegenprobe der Attrappe selbst: der alte Aufruf (create_subprocess_exec unter uvloop) bekommt 0 Byte."""
    async def alt():
        proc = await asyncio.create_subprocess_exec("lsblk", "--json", stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        return out
    assert uvloop.run(alt()) == b""


def test_lsblk_json_unter_uvloop_liefert_daten(apparmor_lsblk):
    data = uvloop.run(_lsblk.lsblk_json(["--output", "NAME"]))
    assert data["blockdevices"][0]["name"] == "sda"


def test_host_disks_unter_uvloop(apparmor_lsblk):
    disks = uvloop.run(pt.list_unmounted_host_disks())
    assert [d.name for d in disks] == ["sda"]                      # Loop-Geräte gefiltert
    disks_all = uvloop.run(pt.list_host_disks())
    assert [d.name for d in disks_all] == ["sda"]


def test_leere_ausgabe_eigener_fehlercode(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "lsblk").write_text("#!/bin/bash\nexit 0\n")
    (bin_dir / "lsblk").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    with pytest.raises(pt.PassthroughError) as e:
        asyncio.run(pt.list_host_disks())
    assert e.value.code == "lsblk_empty"


def test_lsblk_fehlt(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(pt.PassthroughError) as e:
        asyncio.run(pt.list_host_disks())
    assert e.value.code == "lsblk_missing"


def test_kein_create_subprocess_exec_fuer_lsblk():
    src = Path(pt.__file__).read_text(encoding="utf-8")
    assert "create_subprocess_exec" not in src


# --- Installer: Programme mit eigenem AppArmor-Profil (26.04) nicht direkt in Dateien umleiten ------------------

REPO = Path(__file__).resolve().parents[2]
# Profile aus /etc/apparmor.d einer frischen Ubuntu-26.04.1-Installation, die der Installer aufruft.
_PROFILED = ("ssh-keyscan", "lsblk", "systemd-detect-virt")


def test_installer_leitet_profilierte_programme_nicht_in_dateien():
    """Befund 23.11.2026: ``ssh-keyscan … >> known_hosts`` blieb auf 26.04 leer (Profil erlaubt keine Dateien).
    Erlaubt: Pipe (``| tee -a``), ``$(…)``, ``>/dev/null``."""
    bad = []
    for sh in (REPO / "installer").rglob("*.sh"):
        for n, line in enumerate(sh.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            for prog in _PROFILED:
                if prog not in code:
                    continue
                seg = code[code.index(prog):].split("|", 1)[0]
                seg = seg.replace(">/dev/null", "").replace("> /dev/null", "").replace("2>&1", "")
                seg = seg.replace("2>/dev/null", "")
                if ">" in seg and "$(" not in code[:code.index(prog)]:
                    bad.append(f"{sh.relative_to(REPO)}:{n}: {line.strip()}")
    assert not bad, "\n".join(bad)
