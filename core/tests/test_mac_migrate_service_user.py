"""macOS: Umzug einer bestehenden Installation auf das Dienst-Konto _hydrahive (Etappe 3, docs/plans/mac-service-user.md).

installer/lib/mac-migrate-service-user.sh läuft als root aus update-mac.sh. Nachgebauter Mac: alle Werkzeuge
(launchctl, chown, pg_dumpall, sqlite3, colima, curl …) sind Attrappen, die ihre Aufrufe mitschreiben; die Schritte,
die andere Skripte erledigen (Konto anlegen, Postgres-Dienst, Dienst-Dateien), sind ebenfalls Attrappen.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
MIGRATE = INSTALLER / "lib" / "mac-migrate-service-user.sh"


def _exe(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/bash\n" + body)
    p.chmod(0o755)


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    bin_, calls = tmp_path / "bin", tmp_path / "calls.log"
    calls.write_text("")
    rec = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    _exe(bin_ / "sudo", rec + 'while [ $# -gt 0 ]; do case "$1" in -u) shift 2;; -n|-H) shift;; *) break;; esac; done\n'
                              'exec "$@"\n')
    for name in ("chown", "launchctl", "chmod"):
        _exe(bin_ / name, rec)
    _exe(bin_ / "id", 'case "$*" in -u) echo 0;; -un) echo root;; "_hydrahive") exit 0;; *) exec /usr/bin/id "$@";; esac\n')
    _exe(bin_ / "sqlite3", rec + 'case "$2" in .backup*) touch "${2#.backup }";; esac\n')
    _exe(bin_ / "curl", rec + f'[ -f "{tmp_path}/health-fail" ] && exit 22; echo ok\n')
    repo = tmp_path / "repo"
    lib = repo / "installer" / "lib"
    mods = repo / "installer" / "modules-mac"
    lib.mkdir(parents=True)
    mods.mkdir(parents=True)
    (lib / "mac-roles.sh").write_text((INSTALLER / "lib" / "mac-roles.sh").read_text())
    (lib / "mac-migrate-service-user.sh").write_text(MIGRATE.read_text() if MIGRATE.exists() else "exit 9\n")
    _exe(lib / "mac-service-user.sh", rec.replace("$(basename \"$0\")", "service-user") + "echo _hydrahive\n")
    _exe(lib / "mac-postgres-daemon.sh", rec.replace("$(basename \"$0\")", "pg-daemon")
         + f'echo "pg-daemon user=$HH_USER brew=$HH_BREW_USER" >> "{calls}"\n'
         f'[ -f "{tmp_path}/pg-fail" ] && exit 1; exit 0\n')
    _exe(lib / "mac-pg-move.sh", f'echo "pg-move from=$HH_OLD_USER to=$HH_USER dump=$HH_PG_DUMP" >> "{calls}"\n'
         f'[ -f "{tmp_path}/pgmove-fail" ] && exit 1; exit 0\n')
    _exe(lib / "mac-addon-trigger.sh", f'echo "addon-trigger user=$HH_USER" >> "{calls}"\n')
    _exe(lib / "mac-migrate-rollback.sh", f'echo "rollback old=$HH_OLD_USER svc=$HH_SVC_USER backup=$HH_BACKUP" >> "{calls}"\n')
    for m in ("50-launchd.sh", "55-launchd-triggers.sh", "75-agentlink.sh", "70-containers.sh", "55-voice.sh"):
        # wie die echten Module mit set -u: fehlende Pflicht-Variablen fallen hier auf (Befund 22.10.: HH_HOST)
        _exe(mods / m, f'set -u; : "$HH_HOST" "$HH_PORT" "$HH_DATA_DIR" "$HH_CONFIG_DIR" "$HH_REPO_DIR"\n'
                       f'echo "{m} user=$HH_USER brew=$HH_BREW_USER" >> "{calls}"\n')
    data, cfg, log = tmp_path / "data", tmp_path / "etc", tmp_path / "log"
    for d in (data, cfg, log, tmp_path / "hlcfg", tmp_path / "hl"):
        d.mkdir()
    (data / "sessions.db").write_text("db")
    (cfg / "install.conf").write_text("HH_INSTALL_VOICE=yes\n")
    (cfg / "pg_mirror.dsn").write_text("postgresql://x\n")
    (log / "hydrahive2.log").write_text("")
    ts = tmp_path / "ts"
    _exe(ts / "tailscale", rec)
    plists = tmp_path / "plists"
    plists.mkdir()
    for label in ("backend", "agentlink", "agentlink-frontend", "voice-stt", "voice-tts", "colima"):
        (plists / f"io.hydrahive.{label}.plist").write_text("x")
    env = {k: v for k, v in os.environ.items() if not k.startswith("HH_")}   # nichts vom Test-Rechner erben
    env = {**env, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_REPO_DIR": str(repo), "HH_DATA_DIR": str(data),
           "HH_CONFIG_DIR": str(cfg), "HH_LOG_DIR": str(log), "HH_USER": "admin", "HH_BREW_USER": "admin",
           "HH_HL_DIR": str(tmp_path / "hl"), "HH_HL_CONFIG_DIR": str(tmp_path / "hlcfg"),
           "HH_PLIST_DIR": str(plists), "HH_TS_BIN": str(ts), "HH_BACKUP_ROOT": str(tmp_path / "backup"),
           "HH_MIGRATE_WAIT": "1", "HH_COLIMA_STOP": "true"}
    return {"tmp": tmp_path, "env": env, "calls": calls, "cfg": cfg, "data": data}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    script = Path(m["env"]["HH_REPO_DIR"]) / "installer" / "lib" / "mac-migrate-service-user.sh"
    return subprocess.run(["bash", str(script)], env={**m["env"], **extra}, capture_output=True, text=True,
                          timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def _conf(m: dict) -> str:
    return (m["cfg"] / "install.conf").read_text()


def test_full_move_marks_install_conf_last(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "HH_SERVICE_USER=_hydrahive" in _conf(mac)
    assert "HH_INSTALL_VOICE=yes" in _conf(mac)                       # andere Merker bleiben


def test_backup_before_anything_is_stopped(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    first_stop = next(i for i, c in enumerate(calls) if c.startswith("launchctl bootout"))
    backup = next(i for i, c in enumerate(calls) if c.startswith("sqlite3"))
    assert backup < first_stop
    backups = list((mac["tmp"] / "backup").iterdir())
    assert len(backups) == 1 and (backups[0] / "etc" / "install.conf").exists()
    assert (backups[0] / "sessions.db").exists()


def test_services_stopped_ownership_moved_services_rewritten_as_account(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    for label in ("backend", "agentlink", "agentlink-frontend", "voice-stt", "voice-tts", "colima"):
        assert f"launchctl bootout system/io.hydrahive.{label}" in calls, label
    for path in (mac["env"]["HH_REPO_DIR"], str(mac["data"]), str(mac["cfg"]), mac["env"]["HH_HL_DIR"],
                 mac["env"]["HH_HL_CONFIG_DIR"]):
        assert f"chown -R _hydrahive {path}" in calls, path
    for step in ("50-launchd.sh", "55-launchd-triggers.sh", "75-agentlink.sh"):
        assert f"{step} user=_hydrahive brew=admin" in calls, step
    assert "addon-trigger user=_hydrahive" in calls
    assert "55-voice.sh user=_hydrahive brew=admin" in calls          # gewünscht (install.conf)
    assert not any(c.startswith("70-containers.sh") for c in calls)    # nicht gewünscht
    assert f"tailscale set --operator=_hydrahive" in calls


def test_never_takes_over_whole_log_dir(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    log = mac["env"]["HH_LOG_DIR"]
    assert f"chown -R _hydrahive {log}" not in _calls(mac)
    assert f"chown _hydrahive {log}/hydrahive2.log" in _calls(mac)


def test_postgres_moved_with_dump_of_old_user(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    move = [c for c in calls if c.startswith("pg-move")]
    assert move and move[0].startswith("pg-move from=admin to=_hydrahive dump=")
    assert "pg-daemon user=_hydrahive brew=admin" in calls


def test_without_database_no_postgres_step(mac):
    (mac["cfg"] / "pg_mirror.dsn").unlink()
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(c.startswith(("pg-move", "pg-daemon")) for c in _calls(mac))


def test_health_fails_marker_not_set_and_reports_backup(mac):
    (mac["tmp"] / "health-fail").touch()
    r = _run(mac)
    assert r.returncode != 0
    assert "HH_SERVICE_USER" not in _conf(mac)
    assert "Sicherung" in r.stdout + r.stderr


def test_postgres_failure_stops_before_rewriting_services(mac):
    (mac["tmp"] / "pgmove-fail").touch()
    r = _run(mac)
    assert r.returncode != 0
    assert "HH_SERVICE_USER" not in _conf(mac)
    assert not any(c.startswith("50-launchd.sh") for c in _calls(mac))


def test_already_moved_does_nothing(mac):
    (mac["cfg"] / "install.conf").write_text("HH_SERVICE_USER=_hydrahive\n")
    r = _run(mac)
    assert r.returncode == 0
    assert _calls(mac) == []


def test_opt_out(mac):
    r = _run(mac, HH_SERVICE_ACCOUNT="no")
    assert r.returncode == 0
    assert _calls(mac) == []


def test_old_user_root_refused(mac):
    """Ohne echten alten Nutzer (Repo gehört root) nichts anfassen."""
    r = _run(mac, HH_USER="root")
    assert r.returncode != 0
    assert _calls(mac) == []



def _rollback_calls(m: dict) -> list[str]:
    return [c for c in _calls(m) if c.startswith("rollback")]


def test_failure_after_stop_rolls_back_to_old_user(mac):
    """Befund 22.10.2026 (.186): Abbruch beim Datenbank-Import ließ einen halben Umzug zurück – Dateien gehörten dem
    Konto, Dienste dem alten Nutzer, nichts lief. Jetzt: Rückweg auf den alten Stand."""
    (mac["tmp"] / "pgmove-fail").touch()
    r = _run(mac)
    assert r.returncode != 0
    rb = _rollback_calls(mac)
    assert rb and rb[0].startswith("rollback old=admin svc=_hydrahive backup=")
    assert "HH_SERVICE_USER" not in _conf(mac)


def test_health_failure_rolls_back(mac):
    (mac["tmp"] / "health-fail").touch()
    r = _run(mac)
    assert r.returncode != 0
    assert _rollback_calls(mac)


def test_plists_saved_in_backup(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    backup = next((mac["tmp"] / "backup").iterdir())
    assert (backup / "plists" / "io.hydrahive.backend.plist").read_text() == "x"


def test_root_owned_parts_stay_root(mac):
    """Tailscale-Schlüssel und die Logs der root-Dienste (Update, Zusatz-Module, tailscaled) bleiben bei root –
    sonst könnte das Dienst-Konto sie verändern."""
    (mac["data"] / "tailscale").mkdir()
    log = Path(mac["env"]["HH_LOG_DIR"])
    for name in ("hydrahive2-update.log", "hydrahive2-addon.log", "hydrahive2-tailscaled.log"):
        (log / name).write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert f"chown -R root {mac['data']}/tailscale" in calls
    for name in ("hydrahive2-update.log", "hydrahive2-addon.log", "hydrahive2-tailscaled.log"):
        assert f"chown _hydrahive {log / name}" not in calls, name
