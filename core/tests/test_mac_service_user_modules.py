"""macOS: Installer-Bausteine mit Dienst-Konto _hydrahive (docs/plans/mac-service-user.md, Etappe 2).

Der Installer läuft als Mac-Besitzer (alexmo). Alles, was HydraHive gehört (Repo, venv, Daten, Config, Logs) und
alles, was als HydraHive läuft (pip, npm, psql), geht über `sudo -u _hydrahive`; brew über den Mac-Besitzer.
Nachgebauter Mac: sudo/chown/chmod/launchctl/brew/psql sind Attrappen, die ihre Aufrufe mitschreiben.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
MODS = INSTALLER / "modules-mac"
ME = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()


def _exe(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/bash\n" + body)
    p.chmod(0o755)


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    bin_, calls = tmp_path / "bin", tmp_path / "calls.log"
    rec = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    _exe(bin_ / "sudo", rec + 'while [ $# -gt 0 ]; do case "$1" in -u) shift 2;; -n|-H) shift;; *) break;; esac; done\n'
                              'exec "$@"\n')
    for name in ("chown", "chmod", "launchctl", "chflags"):
        _exe(bin_ / name, rec + ("echo '123 0 io.hydrahive.backend'\n" if name == "launchctl" else ""))
    prefix = tmp_path / "brew"
    _exe(prefix / "bin" / "brew", rec + f'case "$1" in --prefix) echo "{prefix}";; esac\nexit 0\n')
    _exe(bin_ / "psql", rec)
    _exe(bin_ / "dscl", 'echo "NFSHomeDirectory: /usr/local/var/hydrahive2/home"\n')
    _exe(bin_ / "npm", rec)
    _exe(bin_ / "openssl", 'echo deadbeef\n')
    repo = tmp_path / "repo"
    (repo / "frontend").mkdir(parents=True)
    (repo / "installer").symlink_to(INSTALLER)
    cfg, data = tmp_path / "etc", tmp_path / "data"
    cfg.mkdir()
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_USER": "_hydrahive", "HH_BREW_USER": ME,
           "HH_BREW": str(prefix / "bin" / "brew"), "HH_REPO_DIR": str(repo), "HH_CONFIG_DIR": str(cfg),
           "HH_DATA_DIR": str(data), "HH_HOST": "127.0.0.1", "HH_PORT": "8001",
           "HH_BACKEND_PLIST": str(tmp_path / "backend.plist"), "HH_LOG_DIR": str(tmp_path / "log"),
           "HH_BREW_CANDIDATES": str(prefix / "bin" / "brew")}
    return {"tmp": tmp_path, "env": env, "calls": calls, "repo": repo, "cfg": cfg, "prefix": prefix}


def _run(m: dict, script: str, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(MODS / script)], env={**m["env"], **extra}, capture_output=True, text=True,
                          timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines() if m["calls"].exists() else []


def test_paths_does_not_take_over_shared_log_dir(mac):
    """/usr/local/var/log gehört auf Intel-Macs Homebrew – nie komplett dem Dienst-Konto übergeben."""
    r = _run(mac, "20-paths.sh")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(c.startswith("chown -R _hydrahive") and c.rstrip().endswith("/log") for c in _calls(mac))
    src = (MODS / "20-paths.sh").read_text()
    assert 'chown -R "$HH_USER" /usr/local/var/log' not in src


def test_paths_prepares_service_log_files(mac):
    r = _run(mac, "20-paths.sh")
    assert r.returncode == 0, r.stdout + r.stderr
    log = mac["env"]["HH_LOG_DIR"]
    for name in ("hydrahive2.log", "hydrahive2-error.log"):
        assert f"chown _hydrahive {log}/{name}" in _calls(mac), _calls(mac)


def test_frontend_builds_as_service_account(mac):
    r = _run(mac, "40-frontend.sh")
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    npm_sudo = [c for c in calls if c.startswith("sudo -u _hydrahive") and " npm " in f" {c} "]
    npm_runs = [c for c in calls if c.startswith("npm ")]
    assert len(npm_sudo) == 2 and len(npm_runs) == 2, calls     # jeder npm-Lauf über das Dienst-Konto


def test_launchd_home_is_service_account_home(mac):
    r = _run(mac, "50-launchd.sh")
    assert r.returncode == 0, r.stdout + r.stderr
    p = plistlib.loads(Path(mac["env"]["HH_BACKEND_PLIST"]).read_bytes())
    assert p["UserName"] == "_hydrahive"
    assert p["EnvironmentVariables"]["HOME"] == "/usr/local/var/hydrahive2/home"


def test_launchd_secret_belongs_to_service_account(mac):
    r = _run(mac, "50-launchd.sh")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"chown _hydrahive {mac['cfg']}/secret_key" in _calls(mac), _calls(mac)


def test_launchd_old_way_home_unchanged(mac):
    """Alter Weg (HH_USER = Mac-Besitzer, kein Konto): HOME bleibt /Users/<name>."""
    r = _run(mac, "50-launchd.sh", HH_USER="admin", HH_BREW_USER="admin")
    assert r.returncode == 0, r.stdout + r.stderr
    p = plistlib.loads(Path(mac["env"]["HH_BACKEND_PLIST"]).read_bytes())
    assert p["EnvironmentVariables"]["HOME"] == "/Users/admin"


def test_nginx_brew_as_brew_user(mac):
    src = (MODS / "60-nginx.sh").read_text()
    assert 'sudo -u "${HH_USER:?HH_USER fehlt}" "$HH_BREW"' not in src
    assert "mac-roles.sh" in src


def _pg_env(m: dict) -> dict:
    lib = m["tmp"] / "pglib"
    _exe(lib / "mac-postgres-daemon.sh", f'echo "daemon user=$HH_USER brew=$HH_BREW_USER" >> "{m["calls"]}"\n')
    _exe(lib / "mac-roles.sh", (INSTALLER / "lib" / "mac-roles.sh").read_text())
    pg = m["prefix"] / "share" / "postgresql@16" / "extension"
    pg.mkdir(parents=True)
    (pg / "vector.control").write_text("x")
    _exe(m["prefix"] / "bin" / "psql", f'echo "psql $*" >> "{m["calls"]}"\n')
    return {"INSTALLER_DIR": str(m["tmp"] / "pginst")}


def _run_pg(m: dict) -> subprocess.CompletedProcess:
    inst = m["tmp"] / "pginst"
    (inst / "modules-mac").mkdir(parents=True, exist_ok=True)
    (inst / "modules-mac" / "48-postgres.sh").write_text((MODS / "48-postgres.sh").read_text())
    if not (inst / "lib").exists():
        (inst / "lib").symlink_to(m["tmp"] / "pglib")
    env = {**m["env"], **_pg_env(m)}
    return subprocess.run(["bash", str(inst / "modules-mac" / "48-postgres.sh")], env=env, capture_output=True,
                          text=True, timeout=60)


def test_postgres_psql_runs_as_service_account(mac):
    """Superuser der neuen Datenbank ist das Dienst-Konto – psql als Mac-Besitzer käme nicht hinein."""
    r = _run_pg(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    psql_sudo = [c for c in calls if c.startswith("sudo -u _hydrahive") and "/bin/psql " in c]
    psql_runs = [c for c in calls if c.startswith("psql ")]
    assert len(psql_runs) == 3 and len(psql_sudo) == 3, calls
    assert all(" -h 127.0.0.1 " in c for c in psql_runs), psql_runs


def test_postgres_dsn_file_private_and_owned_by_service_account(mac):
    r = _run_pg(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    dsn = mac["cfg"] / "pg_mirror.dsn"
    assert dsn.read_text().startswith("postgresql://hydrahive_mirror:")
    assert f"chown _hydrahive {dsn}" in _calls(mac)
    assert oct(dsn.stat().st_mode & 0o777) == "0o600"
