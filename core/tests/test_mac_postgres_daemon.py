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
    # HH_BREW_USER fest: sonst gälte der Besitzer der brew-Attrappe (Test-Nutzer) als Homebrew-Besitzer
    return {**os.environ, "PATH": f"{m['bin']}:{os.environ['PATH']}", "HH_USER": "tester", "HH_BREW_USER": "tester",
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
    env = _env(fake, HH_USER="jemand-anderes", HH_BREW_USER="jemand-anderes")
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
    r = subprocess.run(["bash", str(DAEMON)], env=_env(fake, HH_USER=me, HH_BREW_USER=me), capture_output=True, text=True, timeout=60)
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
    (repo / "frontend" / "dist").mkdir(parents=True)               # fertiges Frontend → kein Neubau (mac-update.md)
    (repo / "frontend" / "dist" / "index.html").write_text("<html/>")
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
    bplist.write_text("mac-backend-start.sh --timeout-graceful-shutdown HH_LOG_DIR")
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


def test_als_root_brew_ueber_vollen_pfad(fake, tmp_path):
    """Befund 21.10.2026 (Test-Mac): update-mac.sh läuft als root, sudo setzt einen PATH ohne Homebrew →
    „brew: command not found“. Das Skript muss brew über den vollen Pfad aufrufen (HH_BREW in Tests)."""
    fake["ready"].touch()
    real = tmp_path / "homebrew" / "bin" / "brew"
    real.parent.mkdir(parents=True)
    (fake["bin"] / "brew").rename(real)
    (fake["bin"] / "id").write_text('#!/bin/bash\ncase "$*" in "-u") echo 0;; "-u tester") echo 501;; *) exec /usr/bin/id "$@";; esac\n')
    (fake["bin"] / "id").chmod(0o755)
    (fake["bin"] / "dscl").write_text(f'#!/bin/bash\necho "NFSHomeDirectory: {fake["home"]}"\n')
    (fake["bin"] / "dscl").chmod(0o755)
    env = _env(fake, HH_BREW=str(real), PATH=f"{fake['bin']}:/usr/bin:/bin")
    r = subprocess.run(["bash", str(DAEMON)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "brew --prefix postgresql@16" in fake["calls"].read_text()


# ── Dienst-Konto (docs/plans/mac-service-user.md) ───────────────────────────────

def _run_svc(m: dict, **extra) -> subprocess.CompletedProcess:
    (m["bin"] / "dscl").write_text(f'#!/bin/bash\necho "NFSHomeDirectory: {m["home"]}"\n')
    (m["bin"] / "dscl").chmod(0o755)
    (m["bin"] / "chown").write_text(f'#!/bin/bash\necho "chown $*" >> "{m["calls"]}"\n')
    (m["bin"] / "chown").chmod(0o755)
    (m["pg"] / "bin" / "initdb").write_text(f'#!/bin/bash\necho "initdb $*" >> "{m["calls"]}"\n'
                                            f'echo "initdb-env LANG=$LANG LC_ALL=$LC_ALL" >> "{m["calls"]}"\n'
                                            'while [ $# -gt 0 ]; do [ "$1" = "-D" ] && mkdir -p "$2" && touch "$2/PG_VERSION"; shift; done\n')
    (m["pg"] / "bin" / "initdb").chmod(0o755)
    data = m["tmp"] / "svcdata" / "postgres"
    # Konto _hydrahive gibt es auf dem Test-Rechner nicht → stat meldet es als Besitzer (chown ist Attrappe)
    (m["bin"] / "stat").write_text('#!/bin/bash\necho _hydrahive\n')
    (m["bin"] / "stat").chmod(0o755)
    env = _env(m, HH_USER="_hydrahive", HH_BREW_USER="tester", HH_PG_DATA=str(data),
               HH_PG_LOG=str(m["tmp"] / "pg.log"), **extra)
    r = subprocess.run(["bash", str(DAEMON)], env=env, capture_output=True, text=True, timeout=60)
    return r


def test_service_account_gets_own_data_dir(fake):
    """Datenordner gehört dem Dienst-Konto (nicht mehr im Homebrew-Ordner des Mac-Besitzers)."""
    fake["ready"].touch()
    r = _run_svc(fake)
    assert r.returncode == 0, r.stdout + r.stderr
    data = fake["tmp"] / "svcdata" / "postgres"
    p = plistlib.loads(fake["plist"].read_bytes())
    assert p["UserName"] == "_hydrahive"
    assert p["ProgramArguments"] == [str(fake["pg"] / "bin" / "postgres"), "-D", str(data)]
    assert "-U _hydrahive" in _calls_text(fake) and f"-D {data}" in _calls_text(fake)   # initdb als Konto
    assert f"chown -R _hydrahive {data}" in _calls_text(fake)
    assert f"chown -R _hydrahive {data.parent}\n" not in _calls_text(fake)          # nicht den ganzen Datenordner


def test_service_account_existing_data_dir_no_initdb(fake):
    fake["ready"].touch()
    data = fake["tmp"] / "svcdata" / "postgres"
    data.mkdir(parents=True)
    (data / "PG_VERSION").write_text("16\n")
    r = _run_svc(fake)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "initdb" not in _calls_text(fake)


def test_brew_runs_as_brew_user_not_service_account(fake):
    """brew gehört dem Mac-Besitzer – als root über sudo -u $HH_BREW_USER, nie als _hydrahive."""
    fake["ready"].touch()
    (fake["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{fake["calls"]}"\n'
                                      '[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (fake["bin"] / "id").write_text('#!/bin/bash\n[ "$1" = "-u" ] && [ -z "$2" ] && echo 0 && exit 0\n'
                                    '[ "$1" = "-un" ] && echo root && exit 0\n'      # als root (Update), nicht als Besitzer
                                    '[ "$1" = "-u" ] && echo 501 && exit 0\nexec /usr/bin/id "$@"\n')
    for f in ("sudo", "id"):
        (fake["bin"] / f).chmod(0o755)
    r = _run_svc(fake)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls_text(fake).splitlines()
    brew_sudo = [c for c in calls if c.startswith("sudo -u") and any(w.endswith("/bin/brew") for w in c.split())]
    assert brew_sudo and all(c.startswith("sudo -u tester ") for c in brew_sudo), brew_sudo
    # Programme AUS Homebrew (initdb) laufen als Dienst-Konto – das ist richtig; brew selbst nie.
    assert any(c.startswith("sudo -u _hydrahive env ") and "/bin/initdb -D" in c for c in calls)


def _calls_text(m: dict) -> str:
    return m["calls"].read_text() if m["calls"].exists() else ""


def test_initdb_gets_fixed_locale(fake):
    """Befund 22.10.2026 (M2, Knopf im Cockpit): Der Update-Dienst läuft ohne LANG – initdb brach mit „invalid locale
    settings“ ab. initdb bekommt darum eine feste Sprache (wie die Homebrew-Formel: en_US.UTF-8)."""
    fake["ready"].touch()
    r = _run_svc(fake)
    assert r.returncode == 0, r.stdout + r.stderr
    init = [c for c in _calls_text(fake).splitlines() if c.startswith("initdb ")]
    assert init and "--locale=en_US.UTF-8" in init[0], init
    assert "initdb-env LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8" in _calls_text(fake)
