"""macOS: PostgreSQL-Daten vom alten Nutzer zum Dienst-Konto umziehen (lib/mac-pg-move.sh, Etappe 3).

Ablauf: Dienst io.hydrahive.postgres läuft (alter Nutzer) → pg_dumpall als alter Nutzer → Dienst anhalten → warten,
bis Port 5432 frei ist (Befund 22.10.2026: der neue Postmaster bekam 127.0.0.1 nicht, weil der alte noch lief) →
neuer Datenordner + Dienst als Konto (mac-postgres-daemon.sh) → Rolle des alten Nutzers anlegen → Import → Prüfung.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
MOVE = INSTALLER / "lib" / "mac-pg-move.sh"


def _exe(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/bash\n" + body)
    p.chmod(0o755)


@pytest.fixture
def pg(tmp_path: Path) -> dict:
    bin_, calls = tmp_path / "bin", tmp_path / "calls.log"
    calls.write_text("")
    rec = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    _exe(bin_ / "sudo", rec + 'while [ $# -gt 0 ]; do case "$1" in -u) shift 2;; -n|-H) shift;; *) break;; esac; done\n'
                              'exec "$@"\n')
    _exe(bin_ / "launchctl", rec)
    _exe(bin_ / "chown", rec)
    _exe(bin_ / "id", 'case "$*" in -u) echo 0;; -un) echo root;; *) exec /usr/bin/id "$@";; esac\n')
    # Port 5432 belegt, bis die Datei port-free existiert (nach N Abfragen)
    _exe(bin_ / "lsof", rec + f'n=$(cat "{tmp_path}/lsof-n" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "{tmp_path}/lsof-n"\n'
                              f'[ "$n" -gt "${{FAKE_BUSY:-0}}" ] && exit 1; echo "postgres 1 admin 7u IPv4 TCP 127.0.0.1:5432 (LISTEN)"\n')
    prefix = tmp_path / "brew"
    pgbin = prefix / "opt" / "postgresql@16" / "bin"
    _exe(pgbin / "pg_dumpall", rec + f'[ -f "{tmp_path}/dump-fail" ] && exit 1; echo "-- dump"; echo "CREATE ROLE admin;"\n')
    _exe(pgbin / "psql", rec + f'cat > /dev/null; [ -f "{tmp_path}/psql-fail" ] && exit 1\n'
                               'case "$*" in *"SELECT count"*) echo 3;; esac; exit 0\n')
    _exe(pgbin / "pg_isready", "exit 0\n")
    _exe(prefix / "bin" / "brew", f'case "$1 $2" in "--prefix postgresql@16") echo "{prefix / "opt" / "postgresql@16"}";; '
                                  f'"--prefix ") echo "{prefix}";; esac\n')
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "mac-roles.sh").write_text((INSTALLER / "lib" / "mac-roles.sh").read_text())
    (lib / "mac-pg-move.sh").write_text(MOVE.read_text() if MOVE.exists() else "exit 9\n")
    _exe(lib / "mac-postgres-daemon.sh", f'echo "pg-daemon user=$HH_USER brew=$HH_BREW_USER" >> "{calls}"\n'
                                         f'[ -f "{tmp_path}/daemon-fail" ] && exit 1; mkdir -p "$HH_PG_DATA"; exit 0\n')
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_OLD_USER": "admin", "HH_USER": "_hydrahive",
           "HH_BREW_USER": "admin", "HH_BREW": str(prefix / "bin" / "brew"), "HH_PG_DUMP": str(tmp_path / "all.sql"),
           "HH_PG_PORT_WAIT": "5", "HH_PG_PLIST": str(tmp_path / "pg.plist"),
           "HH_PG_DATA": str(tmp_path / "newdata")}
    (tmp_path / "pg.plist").write_text("x")
    return {"tmp": tmp_path, "env": env, "calls": calls, "script": lib / "mac-pg-move.sh"}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(m["script"])], env={**m["env"], **extra}, capture_output=True, text=True,
                          timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def test_dump_as_old_user_then_stop_then_new_daemon_then_import(pg):
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(pg)
    i_dump = next(i for i, c in enumerate(calls) if c.startswith("pg_dumpall"))
    i_stop = next(i for i, c in enumerate(calls) if c.startswith("launchctl bootout system/io.hydrahive.postgres"))
    i_new = calls.index("pg-daemon user=_hydrahive brew=admin")
    i_imp = next(i for i, c in enumerate(calls) if c.startswith("psql") and " -f " in f" {c} ")
    assert i_dump < i_stop < i_new < i_imp, calls
    assert calls[i_dump - 1].startswith("sudo -u admin")                # Dump als alter Superuser
    assert (pg["tmp"] / "all.sql").read_text().startswith("-- dump")


def test_dump_file_private(pg):
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    assert oct((pg["tmp"] / "all.sql").stat().st_mode & 0o777) == "0o600"


def test_waits_until_port_is_free(pg):
    r = _run(pg, FAKE_BUSY="3")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sum(1 for c in _calls(pg) if c.startswith("lsof")) >= 4


def test_port_never_free_aborts_before_new_daemon(pg):
    r = _run(pg, FAKE_BUSY="999")
    assert r.returncode != 0
    assert not any(c.startswith("pg-daemon") for c in _calls(pg))


def test_old_role_created_before_import(pg):
    """Im Dump stehen Objekte mit Eigentümer „admin“ – die Rolle muss in der neuen Datenbank existieren."""
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(pg)
    i_role = next(i for i, c in enumerate(calls) if c.startswith("psql") and "admin" in c and "ROLE" in c)
    i_imp = next(i for i, c in enumerate(calls) if c.startswith("psql") and " -f " in f" {c} ")
    assert i_role < i_imp


def test_dump_fails_nothing_stopped(pg):
    (pg["tmp"] / "dump-fail").touch()
    r = _run(pg)
    assert r.returncode != 0
    assert not any(c.startswith("launchctl bootout") for c in _calls(pg))


def test_import_fails_reports_error(pg):
    (pg["tmp"] / "psql-fail").touch()
    r = _run(pg)
    assert r.returncode != 0


def test_import_marker_written(pg):
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (pg["tmp"] / "newdata" / ".hh-imported").exists()


def test_already_moved_no_second_dump(pg):
    """Import schon fertig (Wiederholung nach Abbruch eines späteren Schritts) → nicht noch einmal importieren."""
    (pg["tmp"] / "newdata").mkdir()
    (pg["tmp"] / "newdata" / ".hh-imported").touch()
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(c.startswith("pg_dumpall") for c in _calls(pg))


def test_database_count_mismatch_fails(pg):
    """Import meldet Fehler nur als Text (ohne ON_ERROR_STOP) – darum Datenbanken vorher/nachher zählen."""
    psql = pg["tmp"] / "brew" / "opt" / "postgresql@16" / "bin" / "psql"
    psql.write_text(psql.read_text().replace('echo 3;;', 'n=$(cat "' + str(pg["tmp"]) + '/cnt" 2>/dev/null || echo 2); '
                                             'echo $((n+1)) > "' + str(pg["tmp"]) + '/cnt"; echo $n;;'))
    r = _run(pg)
    assert r.returncode != 0
    assert not (pg["tmp"] / "newdata" / ".hh-imported").exists()


def test_import_reads_a_copy_the_account_can_read(pg):
    """Befund 22.10.2026 (.186): Die Sicherung liegt in einem root-Ordner (0700) – psql als _hydrahive bekam
    „Permission denied“ auf den Dump. Import darum aus einer eigenen Kopie, die dem Konto gehört; danach weg."""
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    imp = next(c for c in _calls(pg) if c.startswith("psql") and " -f " in f" {c} ")
    src = imp.split(" -f ")[1].split()[0]
    assert src != pg["env"]["HH_PG_DUMP"]
    assert f"chown _hydrahive {src}" in _calls(pg)
    assert not Path(src).exists()


def test_unfinished_new_data_dir_moved_aside_not_deleted(pg):
    """Neuer Datenordner ohne Fertig-Merker = Rest eines abgebrochenen Versuchs → beiseite, damit nicht doppelt
    importiert wird. Nichts wird gelöscht."""
    (pg["tmp"] / "newdata").mkdir()
    (pg["tmp"] / "newdata" / "PG_VERSION").write_text("16\n")
    r = _run(pg)
    assert r.returncode == 0, r.stdout + r.stderr
    aside = [p for p in pg["tmp"].iterdir() if p.name.startswith("newdata.unfertig-")]
    assert len(aside) == 1 and (aside[0] / "PG_VERSION").exists()
    calls = _calls(pg)
    i_stop = next(i for i, c in enumerate(calls) if c.startswith("launchctl bootout system/io.hydrahive.postgres"))
    assert i_stop < calls.index("pg-daemon user=_hydrahive brew=admin")
