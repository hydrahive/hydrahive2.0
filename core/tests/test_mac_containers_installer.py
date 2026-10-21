"""installer/modules-mac/70-containers.sh (Plan docs/plans/mac-containers.md): Container über Colima + Incus.

Läuft auf einem nachgebauten Mac: curl holt aus einem lokalen Ordner, colima/incus/sudo/launchctl/sysctl/uname sind
Aufzeichnungen. Die echten Prüfsummen stehen fest im Skript; die Tests setzen eigene für die Schein-Dateien.
"""
from __future__ import annotations

import hashlib
import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SCRIPT = INSTALLER / "modules-mac" / "70-containers.sh"
LINUX_FILES = [INSTALLER / "install.sh", INSTALLER / "update.sh", INSTALLER / "modules" / "70-containers.sh",
               INSTALLER / "lib" / "container-nat.sh", INSTALLER / "lib" / "hh-portforward"]


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    bin_ = tmp_path / "bin"
    calls = tmp_path / "calls.log"
    calls.write_text("")
    log = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    dl = tmp_path / "dl"
    # Schein-Release-Dateien in der Ordnerstruktur von GitHub
    lima_src = tmp_path / "limasrc" / "bin"
    lima_src.mkdir(parents=True)
    (lima_src / "limactl").write_text("#!/bin/bash\n")
    (lima_src / "limactl").chmod(0o755)
    files = {
        "abiosoft/colima/releases/download/v0.10.3/colima-Darwin-x86_64": b"colima-binary",
        "lxc/incus/releases/download/v7.0.2/bin.macos.incus.x86_64": b"incus-binary",
    }
    for rel, data in files.items():
        (dl / rel).parent.mkdir(parents=True, exist_ok=True)
        (dl / rel).write_bytes(data)
    tgz = dl / "lima-vm/lima/releases/download/v2.2.1/lima-2.2.1-Darwin-x86_64.tar.gz"
    tgz.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-czf", str(tgz), "-C", str(tmp_path / "limasrc"), "bin"], check=True)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    shas = {
        "HH_CT_TEST_COLIMA_SHA": sha(dl / "abiosoft/colima/releases/download/v0.10.3/colima-Darwin-x86_64"),
        "HH_CT_TEST_INCUS_SHA": sha(dl / "lxc/incus/releases/download/v7.0.2/bin.macos.incus.x86_64"),
        "HH_CT_TEST_LIMA_SHA": sha(tgz),
    }
    # curl -fsSL --retry 3 -o ZIEL URL  → aus dl/ kopieren
    _exe(bin_ / "curl", log + f'''
out=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; --retry) shift 2;; -*) shift;; *) url="$1"; shift;; esac; done
cp "{dl}/${{url#https://example.test/}}" "$out"
''')
    _exe(bin_ / "sudo", log + 'while [ $# -gt 0 ]; do case "$1" in -u) shift 2;; -n|-H) shift;; *) break;; esac; done\nexec "$@"\n')
    _exe(bin_ / "launchctl", log)
    _exe(bin_ / "xattr", log)
    _exe(bin_ / "chown", log)
    _exe(bin_ / "uname", 'echo "${FAKE_UNAME_M:-x86_64}"\n')
    _exe(bin_ / "id", 'if [ "$#" -eq 1 ] && [ "$1" = "-u" ]; then echo "${FAKE_UID:-501}"; else exec /usr/bin/id "$@"; fi\n')
    _exe(bin_ / "dscl", f'echo "NFSHomeDirectory: {tmp_path}/home"\n')
    _exe(bin_ / "sysctl", 'case "$2" in hw.ncpu) echo "${FAKE_CPUS:-12}";; hw.memsize) echo "${FAKE_MEM:-17179869184}";; esac\n')
    _exe(bin_ / "shasum", 'sha256sum "$3"\n')
    # Nach der Installation stehen colima/incus als Symlinks im bin-Ordner – dort durch Aufzeichnungen ersetzen.
    stub_colima = log + ('case "$1" in status) [ -f "' + str(tmp_path) + '/vm-running" ];; '
                         'start) touch "' + str(tmp_path) + '/vm-running";; esac\n')
    stub_incus = log + ('case "$1 $2" in "network show") [ -f "' + str(tmp_path) + '/net" ];; '
                        '"network create") touch "' + str(tmp_path) + '/net";; esac\n')
    root = tmp_path / "ctroot"
    return {"tmp": tmp_path, "bin": bin_, "calls": calls, "root": root, "shas": shas,
            "stub_colima": stub_colima, "stub_incus": stub_incus,
            "plist": tmp_path / "io.hydrahive.colima.plist", "conf": tmp_path / "etc" / "install.conf",
            "data": tmp_path / "data"}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{m['bin']}:/usr/bin:/bin", "HH_USER": "tester",
           "HH_CONFIG_DIR": str(m["tmp"] / "etc"), "HH_DATA_DIR": str(m["data"]), "HH_LOG_DIR": str(m["tmp"] / "log"),
           "HH_CT_ROOT": str(m["root"]), "HH_CT_PLIST": str(m["plist"]), "HH_CT_DOWNLOAD": "https://example.test",
           **m["shas"], **extra}
    (m["tmp"] / "etc").mkdir(exist_ok=True)
    # Nach dem Entpacken die echten Schein-Binaries durch Aufzeichnungen ersetzen: über einen Vorlauf-Hook geht
    # das nicht – darum legen wir die Aufzeichnungen VOR den Lauf in den Versionsordner, wenn der schon existiert.
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60)


def _ver_dir(m: dict) -> Path:
    return m["root"] / "colima-0.10.3_lima-2.2.1_incus-7.0.2"


def _install_stubs(m: dict) -> None:
    vd = _ver_dir(m)
    _exe(vd / "bin" / "colima", m["stub_colima"])
    _exe(vd / "bin" / "incus", m["stub_incus"])


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def test_downloads_verified_and_vm_started(mac):
    r = _run(mac)
    # Erster Lauf: echte Schein-Dateien heruntergeladen, entpackt; colima ist dann die Schein-Datei „colima-binary“
    # (kein Shell-Skript) → Start schlägt fehl. Darum: Download prüfen, dann Aufzeichnungen einsetzen und erneut.
    vd = _ver_dir(mac)
    assert (vd / "bin" / "colima").read_bytes() == b"colima-binary", r.stdout + r.stderr
    assert (vd / "lima" / "bin" / "limactl").exists()
    assert os.access(vd / "bin" / "incus", os.X_OK)
    _install_stubs(mac)
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert not any(c.startswith("curl") for c in calls)                 # Versionen da → kein neuer Download
    start = [c for c in calls if c.startswith("colima start")]
    assert start == ["colima start hydrahive --runtime incus --vm-type vz --cpu 2 --memory 4 --disk 60 --network-address"]
    assert "incus network create hhnat0 ipv4.address=10.10.0.1/24 ipv4.nat=true ipv6.address=none ipv4.dhcp.ranges=10.10.0.200-10.10.0.250" in calls
    for name in ("colima", "incus", "limactl"):
        assert (mac["root"] / "bin" / name).is_symlink(), name


def test_wrong_checksum_aborts_before_install(mac):
    r = _run(mac, HH_CT_TEST_INCUS_SHA="0" * 64)
    assert r.returncode != 0
    assert "Prüfsumme falsch" in r.stderr
    assert not (_ver_dir(mac) / "bin" / "incus").exists()
    assert not mac["plist"].exists()


def test_daemon_plist_runs_vm_at_boot_as_user(mac):
    _run(mac)
    _install_stubs(mac)
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    p = plistlib.loads(mac["plist"].read_bytes())
    assert p["Label"] == "io.hydrahive.colima"
    assert p["UserName"] == "tester"
    assert p["RunAtLoad"] is True and p["KeepAlive"] is True
    assert p["ProgramArguments"] == [str(mac["root"] / "bin" / "colima"), "start", "hydrahive", "--foreground"]
    assert p["EnvironmentVariables"]["COLIMA_HOME"] == str(mac["data"] / "colima")
    assert f"launchctl load {mac['plist']}" in _calls(mac)


def test_second_run_does_not_restart_running_vm(mac):
    _run(mac)
    _install_stubs(mac)
    _run(mac)
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(c.startswith("colima start") for c in _calls(mac))
    assert not any(c.startswith("incus network create") for c in _calls(mac))


def test_vm_size_capped_to_half_of_host(mac):
    _run(mac)
    _install_stubs(mac)
    r = _run(mac, FAKE_CPUS="2", FAKE_MEM=str(6 * 1024 ** 3), HH_CONTAINERS_CPU="8", HH_CONTAINERS_MEMORY="16")
    assert r.returncode == 0, r.stdout + r.stderr
    start = [c for c in _calls(mac) if c.startswith("colima start")][0]
    assert "--cpu 1 " in start and "--memory 3 " in start


def test_install_conf_marks_containers_wanted(mac):
    mac["conf"].parent.mkdir(parents=True, exist_ok=True)
    mac["conf"].write_text("HH_INSTALL_X=yes\nHH_INSTALL_CONTAINERS=no\n")
    _run(mac)
    _install_stubs(mac)
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = mac["conf"].read_text().splitlines()
    assert "HH_INSTALL_X=yes" in lines
    assert lines.count("HH_INSTALL_CONTAINERS=yes") == 1
    assert "HH_INSTALL_CONTAINERS=no" not in lines


def test_arm64_uses_arm_files():
    text = SCRIPT.read_text()
    arm = text[text.index("  arm64)"):text.index("  x86_64)")]
    assert "colima-Darwin-arm64" in arm and "Darwin-arm64.tar.gz" in arm and "bin.macos.incus.aarch64" in arm
    assert "980ad8bf61a4ca370243f4cb41401a61276dcd2c2502bee7b9b86f9250169f34" in arm


def test_real_checksums_pinned():
    """Die festen Werte entsprechen den veröffentlichten Prüfsummen der Releases (Stand 21.10.2026)."""
    text = SCRIPT.read_text()
    for sha in ("3082737fe8a98afda11cba7d9a20b6e56fe80c6153464beda04bec630758770b",
                "6b776e4bc41f358e6ee01fefcc78e2eb26f11635a0fcff632234af77a566c6c4",
                "a67f1507e299d1995d69ad4cf5d73f2fc81319aab8fc95102dc741f52370e092",
                "9e9eacce88f37e185c346bad73aa6136f738d8cdf8c3bb23cd42b071824bc66e",
                "12aa325c9437223bbdcb8da754e0aafdff948fc168f7537140460f20267762c8"):
        assert sha in text


def test_linux_installer_files_untouched_by_mac_containers():
    """Till: „achte darauf, dass wir die Linux-Installer nicht killen“ – kein Linux-Installer verweist auf das
    Mac-Modul, und das Mac-Modul nutzt keine Linux-Werkzeuge."""
    for f in LINUX_FILES:
        assert "modules-mac/70-containers" not in f.read_text(), f.name
    text = SCRIPT.read_text()
    for bad in ("apt-get", "systemctl", "ufw", "usermod", "/etc/systemd"):
        assert bad not in text, bad


def test_first_start_retried_once(mac):
    """Befund 21.10.2026 (Test-Mac, erster Start über das Cockpit): Colima legt Incus an, `incus remote add` scheitert
    mit EOF (SSH-Sitzung kennt die neue Gruppe noch nicht) → „error starting incus“. Ein zweiter Start klappt."""
    _run(mac)
    vd = _ver_dir(mac)
    flag = mac["tmp"] / "start-count"
    _exe(vd / "bin" / "colima", f'echo "$(basename "$0") $*" >> "{mac["calls"]}"\n' + f'''
case "$1" in
  status) [ -f "{mac["tmp"]}/vm-running" ] ;;
  stop) exit 0 ;;
  start) n=$(cat "{flag}" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "{flag}"
         [ "$n" -ge 2 ] || {{ echo "error starting incus: ... EOF" >&2; exit 1; }}
         touch "{mac["tmp"]}/vm-running" ;;
esac
''')
    _exe(vd / "bin" / "incus", mac["stub_incus"])
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = [c for c in _calls(mac) if c.startswith("colima")]
    assert [c.split()[1] for c in calls if c.split()[1] in ("start", "stop")] == ["start", "stop", "start"]


def test_start_fails_twice_aborts(mac):
    _run(mac)
    vd = _ver_dir(mac)
    _exe(vd / "bin" / "colima", 'case "$1" in status) exit 1;; start) exit 1;; esac\nexit 0\n')
    _exe(vd / "bin" / "incus", mac["stub_incus"])
    r = _run(mac)
    assert r.returncode != 0
    assert not mac["plist"].exists()
