"""macOS: Service-Secrets gehören nicht in die für alle lesbare launchd-plist.

Befund 02.10.2026 (Mac .186): 50-launchd.sh schrieb HH_SECRET_KEY (signiert
alle Logins) und HH_PG_MIRROR_DSN samt Passwort als EnvironmentVariables in
/Library/LaunchDaemons/io.hydrahive.backend.plist (root:wheel 0644). Jeder
lokale Nutzer konnte beides lesen, auch per `launchctl print system/…`.
Linux hat das seit e8e08870 gelöst (EnvironmentFile 0600). Hier: ein
Start-Wrapper liest secret_key und pg_mirror.dsn (beide 0600) selbst ein,
die plist enthält nur noch Pfade. update-mac.sh baut alte plists um.
"""
from __future__ import annotations

import os
import plistlib
import stat
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
LAUNCHD = INSTALLER / "modules-mac" / "50-launchd.sh"
POSTGRES = INSTALLER / "modules-mac" / "48-postgres.sh"
UPDATE = INSTALLER / "update-mac.sh"
WRAPPER = INSTALLER / "lib" / "mac-backend-start.sh"
KEY = "k3y-mit-$onder'zeichen\"und\\backslash" + "x" * 40
DSN = "postgresql://hydrahive_mirror:p%40ss$word@127.0.0.1:5432/hydrahive_mirror"


@pytest.fixture
def fake_mac(tmp_path: Path) -> dict:
    """Fake-Umgebung: sudo/launchctl/brew als Stubs, plist landet in tmp."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    (bin_ / "sudo").write_text('#!/bin/bash\n[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n'
                                    'case "$1" in list) echo "123 0 io.hydrahive.backend";; esac\n')
    (bin_ / "brew").write_text("#!/bin/bash\necho /usr/local\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    cfg = tmp_path / "etc"
    cfg.mkdir()
    (cfg / "secret_key").write_text(KEY + "\n")
    (cfg / "secret_key").chmod(0o600)
    (cfg / "pg_mirror.dsn").write_text(DSN + "\n")
    (cfg / "pg_mirror.dsn").chmod(0o600)
    repo = tmp_path / "repo"
    (repo / "installer" / "lib").mkdir(parents=True)
    (repo / ".venv" / "bin").mkdir(parents=True)
    return {"tmp": tmp_path, "bin": bin_, "cfg": cfg, "repo": repo, "calls": calls,
            "plist": tmp_path / "io.hydrahive.backend.plist"}


def _env(m: dict) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:{os.environ['PATH']}",
            "HH_CONFIG_DIR": str(m["cfg"]), "HH_DATA_DIR": str(m["tmp"] / "data"),
            "HH_REPO_DIR": str(m["repo"]), "HH_USER": "tester", "HH_HOST": "127.0.0.1",
            "HH_PORT": "8001", "HH_BACKEND_PLIST": str(m["plist"])}


def _run_launchd(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(LAUNCHD)], env=_env(m), capture_output=True,
                          text=True, timeout=60)


def test_plist_enthaelt_keine_geheimnisse(fake_mac):
    r = _run_launchd(fake_mac)
    assert r.returncode == 0, r.stderr + r.stdout
    raw = fake_mac["plist"].read_text()
    assert "HH_SECRET_KEY" not in raw and "HH_PG_MIRROR_DSN" not in raw
    assert "x" * 40 not in raw and "p%40ss" not in raw
    env = plistlib.loads(fake_mac["plist"].read_bytes())["EnvironmentVariables"]
    assert env["HH_CONFIG_DIR"] == str(fake_mac["cfg"])


def test_plist_startet_ueber_den_wrapper(fake_mac):
    _run_launchd(fake_mac)
    args = plistlib.loads(fake_mac["plist"].read_bytes())["ProgramArguments"]
    assert args[0] == "/bin/bash" and args[1].endswith("installer/lib/mac-backend-start.sh")
    assert "hydrahive.api.main:app" in args


def test_wrapper_setzt_secrets_aus_den_dateien(fake_mac):
    """Wrapper liest secret_key + pg_mirror.dsn und übergibt sie unverändert."""
    out = subprocess.run(
        ["bash", str(WRAPPER), "/usr/bin/env"], env={**_env(fake_mac), "HH_SECRET_KEY": "",
                                                    "HH_PG_MIRROR_DSN": ""},
        capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    env = dict(line.split("=", 1) for line in out.stdout.splitlines() if "=" in line)
    assert env["HH_SECRET_KEY"] == KEY
    assert env["HH_PG_MIRROR_DSN"] == DSN


def test_wrapper_ohne_dsn_setzt_keinen(fake_mac):
    (fake_mac["cfg"] / "pg_mirror.dsn").unlink()
    out = subprocess.run(["bash", str(WRAPPER), "/usr/bin/env"], env=_env(fake_mac),
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0
    assert "HH_PG_MIRROR_DSN=" not in out.stdout


def test_wrapper_bricht_ohne_secret_key_ab(fake_mac):
    """Lieber nicht starten als mit leerem Schlüssel (Core wirft sonst erst später)."""
    (fake_mac["cfg"] / "secret_key").write_text("")
    out = subprocess.run(["bash", str(WRAPPER), "/usr/bin/env"], env=_env(fake_mac),
                         capture_output=True, text=True, timeout=30)
    assert out.returncode != 0
    assert "secret_key" in out.stderr


def test_secret_dateien_werden_privat(fake_mac):
    """Auch wenn eine alte Installation sie lesbar angelegt hat."""
    for name in ("secret_key", "pg_mirror.dsn"):
        (fake_mac["cfg"] / name).chmod(0o644)
    _run_launchd(fake_mac)
    for name in ("secret_key", "pg_mirror.dsn"):
        mode = stat.S_IMODE((fake_mac["cfg"] / name).stat().st_mode)
        assert mode & 0o077 == 0, f"{name} ist für andere lesbar: {oct(mode)}"


def test_kein_dsn_zwischenfile_mehr(fake_mac):
    """48-postgres.sh legte .pg_dsn_tmp (ohne chmod) an, 50-launchd las es.
    Jetzt wird es nirgends mehr geschrieben oder gelesen, nur Altreste gelöscht."""
    assert ".pg_dsn_tmp" not in POSTGRES.read_text()
    lines = [x for x in LAUNCHD.read_text().splitlines() if ".pg_dsn_tmp" in x]
    assert lines and all(x.strip().startswith("rm -f") for x in lines), lines
    rest = fake_mac["cfg"] / ".pg_dsn_tmp"
    rest.write_text(DSN)
    _run_launchd(fake_mac)
    assert not rest.exists()


OLD_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
<key>Label</key><string>io.hydrahive.backend</string>
<key>EnvironmentVariables</key><dict>
<key>HH_SECRET_KEY</key><string>ALTER-KLARTEXT-SCHLUESSEL</string>
<key>HH_PG_MIRROR_DSN</key><string>postgresql://u:ALTESPASSWORT@127.0.0.1/db</string>
</dict></dict></plist>
"""


def _run_update(m: dict) -> subprocess.CompletedProcess:
    """update-mac.sh in Fake-Umgebung: git/pip als Stubs, Repo verlinkt."""
    (m["bin"] / "git").write_text("#!/bin/bash\nexit 0\n")
    (m["bin"] / "git").chmod(0o755)
    pip = m["repo"] / ".venv" / "bin" / "pip"
    pip.write_text("#!/bin/bash\nexit 0\n")
    pip.chmod(0o755)
    inst = m["repo"] / "installer"
    if not (inst / "modules-mac").exists():
        (inst / "modules-mac").symlink_to(INSTALLER / "modules-mac")
        (inst / "lib" / "mac-backend-start.sh").symlink_to(WRAPPER)
    env = {**_env(m), "HH_UPDATE_LOG": str(m["tmp"] / "update.log")}
    (m["tmp"] / "data").mkdir(exist_ok=True)
    return subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True,
                          text=True, timeout=60)


def test_update_baut_alte_plist_um(fake_mac):
    """Bestehende Installation: plist mit Klartext-Secrets wird beim Update
    neu geschrieben (über den Wrapper), Dienst neu geladen."""
    fake_mac["plist"].write_text(OLD_PLIST)
    r = _run_update(fake_mac)
    assert r.returncode == 0, r.stdout + r.stderr
    raw = fake_mac["plist"].read_text()
    assert "ALTER-KLARTEXT" not in raw and "ALTESPASSWORT" not in raw
    assert "HH_SECRET_KEY" not in raw and "mac-backend-start.sh" in raw
    assert "launchctl load" in fake_mac["calls"].read_text()


def test_update_baut_auch_plist_mit_wrapper_aber_secrets_um(fake_mac):
    """Erkennung über die Secrets selbst, nicht nur über den fehlenden Wrapper."""
    old = OLD_PLIST.replace("<dict>\n<key>Label</key>",
                            "<dict>\n<key>X</key><string>mac-backend-start.sh</string>\n<key>Label</key>")
    fake_mac["plist"].write_text(old)
    r = _run_update(fake_mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ALTER-KLARTEXT" not in fake_mac["plist"].read_text()


def test_update_laesst_neue_plist_in_ruhe(fake_mac):
    """Schon umgebaut: kein erneutes Schreiben, nur Neustart wie bisher."""
    _run_launchd(fake_mac)
    before = fake_mac["plist"].read_bytes()
    fake_mac["calls"].write_text("")
    r = _run_update(fake_mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert fake_mac["plist"].read_bytes() == before
    calls = fake_mac["calls"].read_text()
    assert "launchctl unload" in calls and "launchctl load" in calls
    assert "neu schreiben" not in (fake_mac["tmp"] / "update.log").read_text()
