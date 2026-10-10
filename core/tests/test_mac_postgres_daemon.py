"""macOS: PostgreSQL startet beim Hochfahren (LaunchDaemon), nicht erst nach der Anmeldung.

Befund 10.10.2026: 48-postgres.sh startete die Datenbank mit `brew services start` als normaler
Nutzer → LaunchAgent in ~/Library/LaunchAgents, läuft erst nach Anmeldung. Das Backend
(LaunchDaemon) startet schon beim Booten – nach jedem Neustart lief HydraHive ohne Datamining.
Außerdem nahm update-mac.sh ohne HH_USER fest den Nutzer „admin“ an.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
DAEMON = INSTALLER / "lib" / "mac-postgres-daemon.sh"
POSTGRES = INSTALLER / "modules-mac" / "48-postgres.sh"
UPDATE = INSTALLER / "update-mac.sh"


@pytest.fixture
def fake(tmp_path: Path) -> dict:
    """Fake-Mac: brew/sudo/launchctl als Stubs, Homebrew-Präfix + pg_isready in tmp."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    prefix = tmp_path / "brew"
    pg = prefix / "opt" / "postgresql@16"
    (pg / "bin").mkdir(parents=True)
    ready = tmp_path / "ready"
    (pg / "bin" / "pg_isready").write_text(f'#!/bin/bash\n[ -f "{ready}" ]\n')
    (bin_ / "brew").write_text(
        f'#!/bin/bash\necho "brew $*" >> "{calls}"\n'
        f'case "$1 $2" in "--prefix ") echo "{prefix}";; "--prefix postgresql@16") echo "{pg}";; esac\n')
    (bin_ / "sudo").write_text('#!/bin/bash\n[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    (pg / "bin" / "pg_isready").chmod(0o755)
    home = tmp_path / "home"
    agents = home / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    return {"tmp": tmp_path, "bin": bin_, "calls": calls, "prefix": prefix, "pg": pg, "ready": ready,
            "agent": agents / "homebrew.mxcl.postgresql@16.plist", "home": home,
            "plist": tmp_path / "io.hydrahive.postgres.plist"}


def _env(m: dict, **extra) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:{os.environ['PATH']}", "HH_USER": "tester",
            "HH_PG_PLIST": str(m["plist"]), "HH_PG_WAIT": "2", **extra}


def _run_daemon(m: dict) -> subprocess.CompletedProcess:
    # dscl gibt es unter Linux nicht → Skript fällt auf /Users/<nutzer> zurück; Agent-Pfad hier über
    # einen dscl-Stub auf das tmp-Home lenken.
    (m["bin"] / "dscl").write_text(f'#!/bin/bash\necho "NFSHomeDirectory: {m["home"]}"\n')
    (m["bin"] / "dscl").chmod(0o755)
    return subprocess.run(["bash", str(DAEMON)], env=_env(m), capture_output=True, text=True, timeout=60)


def test_daemon_plist_laeuft_beim_booten_als_hh_user(fake):
    fake["ready"].touch()
    r = _run_daemon(fake)
    assert r.returncode == 0, r.stdout + r.stderr
    pl = plistlib.loads(fake["plist"].read_bytes())
    assert pl["Label"] == "io.hydrahive.postgres"
    assert pl["UserName"] == "tester"
    assert pl["RunAtLoad"] is True and pl["KeepAlive"] is True
    assert pl["ProgramArguments"] == [f"{fake['pg']}/bin/postgres", "-D", f"{fake['prefix']}/var/postgresql@16"]
    assert "launchctl load " + str(fake["plist"]) in fake["calls"].read_text()


def test_brew_services_agent_wird_abgemeldet_und_entfernt(fake):
    fake["ready"].touch()
    fake["agent"].write_text("<plist/>")
    r = _run_daemon(fake)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "brew services stop postgresql@16" in fake["calls"].read_text()
    assert not fake["agent"].exists()


def test_kein_brew_services_start_mehr():
    assert "brew services start" not in POSTGRES.read_text()
    assert "mac-postgres-daemon.sh" in POSTGRES.read_text()


def test_meldet_fehler_wenn_datenbank_nicht_antwortet(fake):
    r = _run_daemon(fake)          # ready-Datei fehlt → pg_isready schlägt fehl
    assert r.returncode == 1
    assert "antwortet" in r.stdout


def test_fremder_besitzer_des_datenverzeichnisses_bricht_ab(fake):
    fake["ready"].touch()
    (fake["prefix"] / "var" / "postgresql@16").mkdir(parents=True)
    env = _env(fake, HH_USER="jemand-anderes")
    (fake["bin"] / "dscl").write_text("#!/bin/bash\nexit 1\n")
    (fake["bin"] / "dscl").chmod(0o755)
    r = subprocess.run(["bash", str(DAEMON)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 1
    assert "abgebrochen" in r.stdout
    assert not fake["plist"].exists()


def test_eigenes_datenverzeichnis_ok(fake):
    fake["ready"].touch()
    (fake["prefix"] / "var" / "postgresql@16").mkdir(parents=True)
    me = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
    (fake["bin"] / "dscl").write_text(f'#!/bin/bash\necho "NFSHomeDirectory: {fake["home"]}"\n')
    (fake["bin"] / "dscl").chmod(0o755)
    r = subprocess.run(["bash", str(DAEMON)], env=_env(fake, HH_USER=me), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


def test_zweiter_lauf_idempotent(fake):
    fake["ready"].touch()
    assert _run_daemon(fake).returncode == 0
    first = fake["plist"].read_bytes()
    assert _run_daemon(fake).returncode == 0
    assert fake["plist"].read_bytes() == first


# ── update-mac.sh ────────────────────────────────────────────────────────────

def _fake_repo(m: dict, owner_env: dict) -> tuple[Path, dict]:
    repo = m["tmp"] / "repo"
    (repo / "installer" / "lib").mkdir(parents=True)
    (repo / "installer" / "lib" / "mac-postgres-daemon.sh").symlink_to(DAEMON)
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "pip").write_text("#!/bin/bash\nexit 0\n")
    (repo / ".venv" / "bin" / "pip").chmod(0o755)
    (m["bin"] / "git").write_text("#!/bin/bash\nexit 0\n")
    (m["bin"] / "git").chmod(0o755)
    cfg = m["tmp"] / "etc"
    cfg.mkdir()
    data = m["tmp"] / "data"
    data.mkdir()
    # Backend-plist „schon umgebaut“, damit update-mac.sh nicht 50-launchd.sh aufruft.
    bplist = m["tmp"] / "backend.plist"
    bplist.write_text("mac-backend-start.sh --timeout-graceful-shutdown")
    env = {**_env(m), "HH_REPO_DIR": str(repo), "HH_CONFIG_DIR": str(cfg), "HH_DATA_DIR": str(data),
           "HH_BACKEND_PLIST": str(bplist), "HH_UPDATE_LOG": str(m["tmp"] / "update.log"), **owner_env}
    return cfg, env


def test_update_stellt_postgres_einmalig_auf_daemon_um(fake):
    fake["ready"].touch()
    cfg, env = _fake_repo(fake, {})
    (cfg / "pg_mirror.dsn").write_text("postgresql://x")
    r = subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert fake["plist"].exists()
    assert "PostgreSQL auf LaunchDaemon umstellen" in (fake["tmp"] / "update.log").read_text()


def test_update_ohne_datenbank_oder_schon_umgestellt_nichts(fake):
    cfg, env = _fake_repo(fake, {})
    r = subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not fake["plist"].exists()                     # kein pg_mirror.dsn → keine Umstellung
    (cfg / "pg_mirror.dsn").write_text("postgresql://x")
    fake["plist"].write_text("vorhanden")
    subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True, text=True, timeout=60)
    assert fake["plist"].read_text() == "vorhanden"       # schon umgestellt → nicht neu schreiben


def test_update_nutzer_ist_besitzer_des_repos_statt_admin(fake):
    _, env = _fake_repo(fake, {})
    env.pop("HH_USER")
    (fake["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{fake["calls"]}"\n'
                                      '[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    r = subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    owner = subprocess.run(["stat", "-c", "%U", env["HH_REPO_DIR"]], capture_output=True, text=True).stdout.strip()
    calls = fake["calls"].read_text()
    assert f"sudo -u {owner} git pull" in calls
    assert "sudo -u admin " not in calls or owner == "admin"
