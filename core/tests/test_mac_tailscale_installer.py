"""installer/modules-mac/80-tailscale.sh (Plan docs/plans/mac-tailscale.md): tailscaled ohne App.

Nachgebauter Mac: curl holt Go aus einem lokalen Ordner, der Schein-„go“ legt tailscale/tailscaled an,
launchctl/sudo/sysctl/uname sind Aufzeichnungen.
"""
from __future__ import annotations

import hashlib
import os
import plistlib
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SCRIPT = INSTALLER / "modules-mac" / "80-tailscale.sh"


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def _go_tarball(calls: Path, tmp: Path) -> bytes:
    """go/bin/go: „install …“ legt $GOBIN/tailscale und tailscaled an (Aufzeichnungen) und protokolliert die Umgebung."""
    ts = (f'#!/bin/bash\necho "tailscale $*" >> "{calls}"\n'
          f'case "$1" in status) [ -f "{tmp}/ts-up" ] && exit 0; echo "Logged out."; exit 1;; esac\nexit 0\n')
    go = (f'#!/bin/bash\necho "go $* GOTOOLCHAIN=$GOTOOLCHAIN GOFLAGS=$GOFLAGS" >> "{calls}"\n'
          f'echo "go-env CGO_ENABLED=$CGO_ENABLED" >> "{calls}"\n'
          'mkdir -p "$GOBIN"\n'
          f"cat > \"$GOBIN/tailscale\" <<'EOS'\n{ts}EOS\n"
          'printf "#!/bin/bash\\nexit 0\\n" > "$GOBIN/tailscaled"\n'
          'chmod 755 "$GOBIN/tailscale" "$GOBIN/tailscaled"\n')
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = go.encode()
        info = tarfile.TarInfo("go/bin/go")
        info.size = len(data)
        info.mode = 0o755
        tar.addfile(info, BytesIO(data))
    return buf.getvalue()


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    bin_ = tmp_path / "bin"
    calls = tmp_path / "calls.log"
    calls.write_text("")
    log = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    dl = tmp_path / "dl"
    dl.mkdir()
    tgz = _go_tarball(calls, tmp_path)
    (dl / "go1.27.3.darwin-amd64.tar.gz").write_bytes(tgz)
    (dl / "go1.27.3.darwin-arm64.tar.gz").write_bytes(tgz)
    _exe(bin_ / "curl", log + f'''
out=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; --retry) shift 2;; -*) shift;; *) url="$1"; shift;; esac; done
cp "{dl}/$(basename "$url")" "$out"
''')
    _exe(bin_ / "sudo", log + 'exec "$@"\n')
    _exe(bin_ / "launchctl", log + f'case "$1" in list) [ -f "{tmp_path}/ts-pid" ] && echo "77 0 io.hydrahive.tailscaled";; '
                                   f'load) touch "{tmp_path}/ts-up";; esac\nexit 0\n')
    _exe(bin_ / "chown", log)
    _exe(bin_ / "uname", 'echo "${FAKE_UNAME_M:-x86_64}"\n')
    _exe(bin_ / "id", 'if [ "$#" -eq 1 ] && [ "$1" = "-u" ]; then echo 0; else exec /usr/bin/id "$@"; fi\n')
    _exe(bin_ / "shasum", 'sha256sum "$3"\n')
    return {"tmp": tmp_path, "bin": bin_, "calls": calls, "root": tmp_path / "tsroot",
            "plist": tmp_path / "io.hydrahive.tailscaled.plist", "conf": tmp_path / "etc" / "install.conf",
            "sha": hashlib.sha256(tgz).hexdigest(), "app": tmp_path / "Tailscale.app", "data": tmp_path / "data"}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    (m["tmp"] / "etc").mkdir(exist_ok=True)
    env = {**os.environ, "PATH": f"{m['bin']}:/usr/bin:/bin", "HH_USER": "tester", "HH_TS_WAIT": "2",
           "HH_CONFIG_DIR": str(m["tmp"] / "etc"), "HH_DATA_DIR": str(m["data"]), "HH_LOG_DIR": str(m["tmp"] / "log"),
           "HH_TS_ROOT": str(m["root"]), "HH_TS_PLIST": str(m["plist"]), "HH_TS_APP": str(m["app"]),
           "HH_GO_DOWNLOAD": "https://example.test/dl", "HH_TS_TEST_GO_SHA": m["sha"], **extra}
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def test_builds_fixed_version_and_starts_daemon(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    go = [c for c in calls if c.startswith("go install")]
    # Version eingebrannt wie build_dist.sh (sonst zeigt `tailscale version` „…-ERR-BuildInfo“)
    assert go == ["go install -ldflags -X tailscale.com/version.longStamp=1.104.2-hydrahive "
                  "-X tailscale.com/version.shortStamp=1.104.2 "
                  "tailscale.com/cmd/tailscale@v1.104.2 tailscale.com/cmd/tailscaled@v1.104.2 "
                  "GOTOOLCHAIN=local GOFLAGS=-trimpath"]
    for name in ("tailscale", "tailscaled"):
        assert (mac["root"] / "1.104.2" / name).exists()
        assert (mac["root"] / "bin" / name).is_symlink()
    assert f"launchctl load {mac['plist']}" in calls
    assert "tailscale set --operator=tester" in calls


def test_daemon_plist_root_at_boot(mac):
    _run(mac)
    p = plistlib.loads(mac["plist"].read_bytes())
    assert p["Label"] == "io.hydrahive.tailscaled"
    assert "UserName" not in p                                   # root: utun
    assert p["RunAtLoad"] is True and p["KeepAlive"] is True
    state = mac["data"] / "tailscale"
    assert p["ProgramArguments"] == [str(mac["root"] / "bin" / "tailscaled"), f"--state={state}/tailscaled.state",
                                     f"--statedir={state}"]


def test_wrong_go_checksum_aborts(mac):
    r = _run(mac, HH_TS_TEST_GO_SHA="0" * 64)
    assert r.returncode != 0
    assert "Prüfsumme falsch" in r.stderr
    assert not (mac["root"] / "1.104.2" / "tailscaled").exists()
    assert not mac["plist"].exists()


def test_existing_app_is_left_alone(mac):
    mac["app"].mkdir()
    r = _run(mac)
    assert r.returncode == 0
    assert "Tailscale-App" in r.stdout
    assert _calls(mac) == []
    assert not mac["plist"].exists()


def test_second_run_no_rebuild_no_restart(mac):
    _run(mac)
    (mac["tmp"] / "ts-pid").write_text("")                       # Dienst läuft
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert not any(c.startswith(("go ", "curl")) for c in calls)
    assert not any(c.startswith(("launchctl load", "launchctl unload")) for c in calls)


def test_daemon_not_running_gets_loaded(mac):
    _run(mac)
    mac["calls"].write_text("")
    r = _run(mac)                                                # gebaut, aber kein Prozess (ts-pid fehlt)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"launchctl load {mac['plist']}" in _calls(mac)


def test_install_conf_marks_wanted(mac):
    mac["conf"].parent.mkdir(parents=True, exist_ok=True)
    mac["conf"].write_text("HH_INSTALL_CONTAINERS=yes\nHH_INSTALL_TAILSCALE=no\n")
    _run(mac)
    lines = mac["conf"].read_text().splitlines()
    assert "HH_INSTALL_CONTAINERS=yes" in lines
    assert lines.count("HH_INSTALL_TAILSCALE=yes") == 1 and "HH_INSTALL_TAILSCALE=no" not in lines


def test_arm64_uses_arm_go(mac):
    r = _run(mac, FAKE_UNAME_M="arm64")
    assert r.returncode == 0, r.stdout + r.stderr
    assert any("go1.27.3.darwin-arm64.tar.gz" in c for c in _calls(mac) if c.startswith("curl"))


def test_real_go_checksums_pinned():
    text = SCRIPT.read_text()
    assert "b6f8e931e4ab497fcde6da8ae4499a58f9d258e55c8a80824a516eae5950a750" in text
    assert "dd3908cf20959d798c1e06ebe5b72213f0505ce01373b40ce3110975a6cd99c2" in text


def test_no_linux_tools_and_linux_untouched():
    text = SCRIPT.read_text()
    for bad in ("apt-get", "systemctl", "install.sh |", "tailscale.com/install.sh"):
        assert bad not in text, bad
    for f in (INSTALLER / "install.sh", INSTALLER / "update.sh", INSTALLER / "modules" / "80-tailscale.sh"):
        assert "modules-mac/80-tailscale" not in f.read_text()


def test_build_without_apple_linker(mac):
    """Befund 23.10.2026 (Tester, M-Mac, macOS 27): Apples Kommandozeilenwerkzeuge passten nicht zum SDK
    („tapi error: unknown architecture arm64e.x1“) – der Bau von tailscaled brach beim Linken ab. Ohne cgo linkt Go
    selbst; tailscaled läuft so genauso (live geprüft: Tailnet, MagicDNS, Ping über das LAN)."""
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "go-env CGO_ENABLED=0" in _calls(mac)
