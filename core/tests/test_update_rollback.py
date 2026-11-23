"""Etappe U4 (docs/specs/update-rollback.md §3.3/§3.4/§4): Prüfung nach dem Update und automatischer Rückweg.

Die Tests fahren den ECHTEN Kopf von update.sh (Sperre, Sicherung, Pull, trap) und das ECHTE Ende (Neustart, Phase C) gegen ein
Attrappen-Repo; systemctl, curl und journalctl sind Attrappen (tests/_update_fakes.py), der echte Dienst wird nie berührt.
Je Fehlerfall: Rückweg greift, kaputter Stand liegt in kaputt/ (nichts gelöscht), Schlusszeile stimmt.
Gegenprobe ohne Fix: HH_TEST_NO_ROLLBACK=1 schaltet den Rückweg ab → die Fehlerfall-Tests werden rot
(und test_*_gegenprobe belegt das je Fall im Test selbst).
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from tests.test_update_safety import (
    LIB, SNAP, UPDATE, _backups, _env, _git, _head_script, _meta, _push_new_commit, make_env,
)



@pytest.fixture
def env(tmp_path: Path) -> dict:
    """Dieselbe Attrappen-Umgebung wie in test_update_safety (Origin, Arbeitskopie, Daten, Fakes)."""
    return make_env(tmp_path)


NO_ROLLBACK = os.environ.get("HH_TEST_NO_ROLLBACK") == "1"
UPDATE_TEXT = UPDATE.read_text()
# Das echte Ende von update.sh: Neustart, Phase C, Erfolg, F9 (Systemupgrade), Warnungen.
END_BLOCK = UPDATE_TEXT[UPDATE_TEXT.index('log "Service neu starten"'):]

HELPERS = r'''
hh_system_upgrade() { echo "SYSTEMUPGRADE-LAEUFT"; touch "$HH_DATA_DIR/.systemupgrade-lief"; }
HH_BRIDGE_STOPPED=0
modify_db() {
  python3 -c "import sqlite3;c=sqlite3.connect('$HH_DATA_DIR/sessions.db');c.execute('create table if not exists neu_tabelle(a)');c.execute(\"insert into messages(text) values('NEU-NACH-UPDATE')\");c.commit();c.close()"
}
'''

PRELUDES = {
    "ok": "",
    "apt": 'echo NEU > "$HH_REPO_DIR/frontend/dist/index.html"; err "apt-Upgrade fehlgeschlagen"',          # E4
    "pip": 'err "pip install fehlgeschlagen"',                                                              # E5
    "bau": 'err "Frontend-Bau fehlgeschlagen – das laufende Frontend (dist) ist unverändert."',              # E6
    "migration": 'modify_db',                                                                                # E7 (+ Dienst startet nicht)
    "schleife": 'modify_db',                                                                                 # E7 (Neustart-Schleife)
    "health": 'modify_db',                                                                                   # E8
}


def _run(e: dict, case: str, *, rollback: bool = True, prelude: str | None = None, **extra: str) -> subprocess.CompletedProcess:
    pre = PRELUDES[case] if prelude is None else prelude
    script = _head_script(e) + HELPERS + 'cd "$HH_REPO_DIR"\n' + pre + "\n" + END_BLOCK
    if NO_ROLLBACK or not rollback:
        extra["HH_UPDATE_ROLLBACK"] = "0"
    return subprocess.run(["bash", "-c", script], env=_env(e, **extra), capture_output=True, text=True, timeout=120, cwd=e["repo"])


def _last(r: subprocess.CompletedProcess) -> str:
    return [l for l in r.stdout.splitlines() if l.strip()][-1]


def _sysd(e: dict) -> Path:
    return e["tmp"] / "sysd"


def _calls(e: dict) -> str:
    return (_sysd(e) / "calls.log").read_text() if (_sysd(e) / "calls.log").exists() else ""


def _rows(db: Path) -> list[str]:
    con = sqlite3.connect(db)
    try:
        return [r[0] for r in con.execute("SELECT text FROM messages WHERE text LIKE 'NEU%'")]
    finally:
        con.close()


def _setup(e: dict) -> tuple[str, str]:
    """Neuer Commit auf origin; liefert (alt, neu)."""
    old = _git(e["repo"], "rev-parse", "HEAD")
    new = _push_new_commit(e)
    return old, new


def _kaputt_dir(e: dict) -> Path:
    (d,) = _backups(e)
    return d / "kaputt"


# --- Erfolg: Phase C bestanden, F9, E10 --------------------------------------------------------------------------

def test_erfolg_prueft_health_und_markiert_ok(env):
    old, new = _setup(env)
    r = _run(env, "ok")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _last(r) == "HH-UPDATE-ENDE: ok"
    (d,) = _backups(env)
    assert _meta(d)["STATUS"] == "ok" and _meta(d)["RESTARTED"] == "1"
    assert not (d / "kaputt").exists()
    assert "curl" in _calls(env) or "curl" in (_sysd(env) / "calls.log").read_text()
    assert _git(env["repo"], "rev-parse", "HEAD") == new


def test_f9_systemupgrade_erst_nach_bestandener_pruefung(env):
    _setup(env)
    r = _run(env, "ok")
    assert r.returncode == 0
    i_ok, i_up = r.stdout.index("Update erfolgreich"), r.stdout.index("SYSTEMUPGRADE-LAEUFT")
    assert i_ok < i_up
    assert "Prüfung nach dem Neustart" in r.stdout and r.stdout.index("Prüfung nach dem Neustart") < i_ok


def test_f9_systemupgrade_laeuft_nicht_wenn_die_pruefung_scheitert(env):
    old, new = _setup(env)
    (_sysd(env) / "nostart_commits").write_text(new + "\n")
    r = _run(env, "migration")
    assert r.returncode != 0
    assert "SYSTEMUPGRADE-LAEUFT" not in r.stdout and not (env["data"] / ".systemupgrade-lief").exists()


def test_f9_struktur_upgrade_steht_nach_der_pruefung_nicht_davor():
    code = "\n".join(l for l in UPDATE_TEXT.splitlines() if not l.lstrip().startswith("#"))
    assert code.count("hh_system_upgrade") == 1 and code.index("hh_system_upgrade") > code.index("hh_safety_verify")
    assert code.index("hh_ensure_auto_updates") < code.index("hh_safety_verify")


def test_e10_warnungen_werden_gesammelt_und_am_ende_ausgegeben_kein_rueckweg(env):
    _setup(env)
    r = _run(env, "ok", prelude='hh_warn "Samba-Update fehlgeschlagen"; hh_warn "nginx-Setup fehlgeschlagen"')
    assert r.returncode == 0 and _last(r) == "HH-UPDATE-ENDE: ok" or "HH-UPDATE-WARNUNG" in r.stdout
    lines = [l for l in r.stdout.splitlines() if l.startswith("HH-UPDATE-WARNUNG: ")]
    assert lines == ["HH-UPDATE-WARNUNG: Samba-Update fehlgeschlagen", "HH-UPDATE-WARNUNG: nginx-Setup fehlgeschlagen"]
    assert r.stdout.index("Update erfolgreich") < r.stdout.index(lines[0])
    (d,) = _backups(env)
    assert _meta(d)["STATUS"] == "ok" and not (d / "kaputt").exists()


def test_e10_struktur_kein_stilles_log_weiter_mehr():
    code = [l for l in UPDATE_TEXT.splitlines() if not l.lstrip().startswith("#")]
    still = [l for l in code if ("|| log" in l and ("weiter" in l or "failed" in l))]
    assert still == [], still
    assert sum("|| hh_warn" in l for l in code) >= 15


# --- E4/E5/E6: Fehler vor dem Neustart – Code und Frontend zurück, DB unangetastet ---------------------------------

def test_e4_apt_fehler_rueckweg_code_und_dist(env):
    old, new = _setup(env)
    r = _run(env, "apt")
    assert r.returncode != 0
    assert _last(r) == f"HH-UPDATE-ENDE: fehler apt-Upgrade fehlgeschlagen – auf {old[:8]} zurückgesetzt"
    assert _git(env["repo"], "rev-parse", "HEAD") == old
    assert (env["repo"] / "frontend" / "dist" / "index.html").read_text() == "ALT"          # aus der Sicherung
    assert (env["repo"] / "frontend" / "dist.kaputt" / "index.html").read_text().strip() == "NEU"   # nichts gelöscht
    (d,) = _backups(env)
    assert _meta(d)["STATUS"] == "zurueckgesetzt"
    assert (d / "kaputt").is_dir() and (d / "kaputt" / "git-diff.stat").is_file()
    assert (d / "sessions.db.zst").is_file(), "die Sicherung bleibt"


def test_e4_gegenprobe_ohne_rueckweg_bleibt_neuer_code(env):
    old, new = _setup(env)
    r = _run(env, "apt", rollback=False)
    assert _git(env["repo"], "rev-parse", "HEAD") == new                      # ohne Fix: halber Stand bleibt
    assert "zurückgesetzt" not in _last(r) and _last(r).startswith("HH-UPDATE-ENDE: fehler apt-Upgrade fehlgeschlagen")
    assert (env["repo"] / "frontend" / "dist" / "index.html").read_text().strip() == "NEU"


def test_e5_pip_fehler_rueckweg_mit_venv_aus_sicherung(env):
    """Hat sich pyproject geändert, ist das venv gesichert und wird zurückgeholt; der kaputte Stand liegt als .venv.kaputt."""
    v = env["repo"] / ".venv" / "bin"
    v.mkdir(parents=True)
    (v / "python").write_text("#!/bin/bash\n[ \"$1\" = -c ] && echo 3.12 && exit 0\nexit 0\n")
    (v / "python").chmod(0o755)
    (v / "pip").write_text("#!/bin/bash\nexit 0\n")
    (v / "pip").chmod(0o755)
    (env["repo"] / ".gitignore").write_text(".venv/\n")
    d_sys = env["tmp"] / "usrbin"
    d_sys.mkdir()
    for n in ("python3", "python3.13", "python3.12"):
        (d_sys / n).write_text("#!/bin/bash\n[ \"$1\" = -c ] && echo 3.12 && exit 0\nexec /usr/bin/python3 \"$@\"\n")
        (d_sys / n).chmod(0o755)
    (env["seed"] / "core" / "pyproject.toml").write_text("[project]\nname='x'\ndependencies=['neu']\n")
    _git(env["seed"], "commit", "-qam", "dep")
    _git(env["seed"], "push", "-q", str(env["origin"]), "main")
    old = _git(env["repo"], "rev-parse", "HEAD")
    r = _run(env, "pip", prelude='echo kaputt > "$HH_REPO_DIR/.venv/bin/NEU"; err "pip install fehlgeschlagen"', HH_PYTHON_BIN_DIR=str(d_sys))
    assert _last(r) == f"HH-UPDATE-ENDE: fehler pip install fehlgeschlagen – auf {old[:8]} zurückgesetzt", r.stdout + r.stderr
    (d,) = _backups(env)
    assert _meta(d)["VENV_BACKED_UP"] == "1"
    assert not (env["repo"] / ".venv" / "bin" / "NEU").exists()                 # venv wieder wie vorher
    assert (env["repo"] / ".venv.kaputt" / "bin" / "NEU").exists()              # der kaputte Stand bleibt liegen


def test_e5_gegenprobe(env):
    old, new = _setup(env)
    r = _run(env, "pip", rollback=False)
    assert _git(env["repo"], "rev-parse", "HEAD") == new and "zurückgesetzt" not in _last(r)


def test_e6_bauFehler_dist_unberuehrt_und_db_schritt_uebersprungen(env):
    old, new = _setup(env)
    before = (env["data"] / "sessions.db").read_bytes()
    r = _run(env, "bau")
    assert _last(r).startswith("HH-UPDATE-ENDE: fehler Frontend-Bau fehlgeschlagen") and _last(r).endswith(f"– auf {old[:8]} zurückgesetzt")
    assert _git(env["repo"], "rev-parse", "HEAD") == old
    assert (env["repo"] / "frontend" / "dist" / "index.html").read_text() == "ALT"
    assert "Datenbank unverändert (kein Neustart mit neuem Code) – übersprungen" in r.stdout
    assert not (_kaputt_dir(env) / "ORT-DB.txt").exists(), "keine DB zur Seite gelegt, weil nie neu gestartet"
    assert (env["data"] / "sessions.db").read_bytes() == before                  # DB-Datei nicht angefasst
    assert "systemctl restart hydrahive2.service" not in _calls(env)


def test_e6_gegenprobe(env):
    old, new = _setup(env)
    r = _run(env, "bau", rollback=False)
    assert _git(env["repo"], "rev-parse", "HEAD") == new and "zurückgesetzt" not in _last(r)


# --- E7/E8: Neustart mit neuem Code scheitert – Rückweg INKLUSIVE DB ----------------------------------------------

def _assert_db_rollback(e: dict, r: subprocess.CompletedProcess, old: str, reason_start: str) -> None:
    assert r.returncode != 0
    last = _last(r)
    assert last.startswith(f"HH-UPDATE-ENDE: fehler {reason_start}") and last.endswith(f"– auf {old[:8]} zurückgesetzt"), last
    assert _git(e["repo"], "rev-parse", "HEAD") == old
    assert _rows(e["data"] / "sessions.db") == [], "DB wieder auf dem Stand der Sicherung (ohne die Zeile nach dem Update)"
    k = _kaputt_dir(e)
    ort = Path((k / "ORT-DB.txt").read_text().strip())
    assert _rows(ort / "sessions.db") == ["NEU-NACH-UPDATE"], "der kaputte Stand liegt unverändert zur Seite, nichts gelöscht"
    for name in ("git-diff.stat", "etc-hydrahive2-neu.tar", "journal.txt"):
        assert (k / name).is_file(), name
    (d,) = _backups(e)
    assert _meta(d)["STATUS"] == "zurueckgesetzt" and (d / "sessions.db.zst").is_file()
    assert "systemctl start hydrahive2.service" in _calls(e)


def test_e7_migration_dienst_startet_nicht_rueckweg_mit_db(env):
    old, new = _setup(env)
    (_sysd(env) / "nostart_commits").write_text(new + "\n")
    r = _run(env, "migration")
    _assert_db_rollback(env, r, old, "Health-Prüfung nach 1 s nicht ok (Dienst nicht aktiv)")


def test_e7_gegenprobe(env):
    old, new = _setup(env)
    (_sysd(env) / "nostart_commits").write_text(new + "\n")
    r = _run(env, "migration", rollback=False)
    assert _git(env["repo"], "rev-parse", "HEAD") == new and _rows(env["data"] / "sessions.db") == ["NEU-NACH-UPDATE"]
    assert "zurückgesetzt" not in _last(r)


def test_e7_neustart_schleife_wird_erkannt(env):
    old, new = _setup(env)
    (_sysd(env) / "loop_commits").write_text(new + "\n")                          # mit dem neuen Stand steigt NRestarts bei jeder Abfrage
    r = _run(env, "schleife", HH_UPDATE_HEALTH_TIMEOUT="3")
    _assert_db_rollback(env, r, old, "Dienst startet in einer Schleife neu")


def test_e7_migrationsstand_zu_niedrig_loest_rueckweg_aus(env):
    """Dienst läuft und antwortet, aber schema_version liegt unter der höchsten Migrationsdatei des neuen Stands."""
    old, new = _setup(env)
    mig = env["seed"] / "core" / "src" / "hydrahive" / "db" / "migrations"       # Migrationen gehören zum NEUEN Commit
    mig.mkdir(parents=True)
    for n in (1, 2, 5):
        (mig / f"{n:03d}_x.sql").write_text("select 1;")
    _git(env["seed"], "add", "-A")
    _git(env["seed"], "commit", "-qm", "migrationen")
    _git(env["seed"], "push", "-q", str(env["origin"]), "main")
    con = sqlite3.connect(env["data"] / "sessions.db")
    con.execute("CREATE TABLE schema_version(version INTEGER, applied_at TEXT)")
    con.execute("INSERT INTO schema_version VALUES (3, 'x')")
    con.commit()
    con.close()
    # die Sicherung enthält schema_version=3; modify_db ändert danach die DB
    r = _run(env, "migration")
    _assert_db_rollback(env, r, old, "Migrationen nicht durchgelaufen (DB-Version 3, erwartet 5)")


def test_e8_health_antwortet_nicht_rueckweg(env):
    old, new = _setup(env)
    (_sysd(env) / "bad_health_commits").write_text(new + "\n")                       # Dienst läuft, /api/health scheitert (Import-Fehler)
    r = _run(env, "health")
    _assert_db_rollback(env, r, old, "Health-Prüfung nach 1 s nicht ok (/api/health antwortet nicht)")


def test_e8_falscher_commit_im_health_loest_rueckweg_aus(env):
    old, new = _setup(env)
    (_sysd(env) / "health_commit_override").write_text("f" * 40)
    r = _run(env, "health")
    assert _last(r).startswith("HH-UPDATE-ENDE: fehler Health-Prüfung nach 1 s nicht ok (/api/health meldet Commit ffffffff statt " + new[:8])
    assert _git(env["repo"], "rev-parse", "HEAD") == old


def test_e8_gegenprobe(env):
    old, new = _setup(env)
    (_sysd(env) / "bad_health_commits").write_text(new + "\n")
    r = _run(env, "health", rollback=False)
    assert _git(env["repo"], "rev-parse", "HEAD") == new and "zurückgesetzt" not in _last(r)


def test_health_wartezeit_ist_einstellbar_und_pruefung_wartet_nicht_ewig(env):
    _setup(env)
    import time
    (_sysd(env) / "bad_health_commits").write_text(_git(env["origin"], "rev-parse", "main") + "\n")
    t = time.time()
    r = _run(env, "health", HH_UPDATE_HEALTH_TIMEOUT="2", HH_UPDATE_HEALTH_INTERVAL="0.5", rollback=False)
    assert "nach 2 s nicht ok" in _last(r) and time.time() - t < 30


# --- E15: DB-Sicherung fehlt – kein Code-Rückweg --------------------------------------------------------------------

def test_e15_ohne_db_sicherung_kein_code_rueckweg(env):
    old, new = _setup(env)
    (_sysd(env) / "nostart_commits").write_text(new + "\n")
    prelude = 'modify_db; rm -f "$HH_BACKUP_DIR"/sessions.db.zst "$HH_BACKUP_DIR"/sessions.db.gz'
    r = _run(env, "migration", prelude=prelude)
    last = _last(r)
    assert last.startswith("HH-UPDATE-ENDE: fehler ") and "Rückweg nicht möglich: DB-Sicherung fehlt oder ist nicht lesbar, Sicherung in " in last
    assert _git(env["repo"], "rev-parse", "HEAD") == new, "lieber ein halber Dienst als alter Code auf neuer DB"
    assert _rows(env["data"] / "sessions.db") == ["NEU-NACH-UPDATE"], "die DB wurde nicht angefasst"
    (d,) = _backups(env)
    assert _meta(d)["STATUS"] == "rueckweg_unvollstaendig" and not (d / "kaputt").exists()


def test_e15_unlesbare_sicherung_gilt_wie_fehlende(env):
    old, new = _setup(env)
    (_sysd(env) / "nostart_commits").write_text(new + "\n")
    r = _run(env, "migration", prelude='modify_db; head -c 100 /dev/urandom > "$HH_BACKUP_DIR"/sessions.db.zst')
    assert "Rückweg nicht möglich" in _last(r) and _git(env["repo"], "rev-parse", "HEAD") == new


# --- E12: ein Rückweg-Schritt scheitert – die übrigen laufen weiter --------------------------------------------------

def test_e12_gescheiterter_schritt_bricht_den_rueckweg_nicht_ab(env):
    old, new = _setup(env)
    # Defektes venv-Archiv in der Sicherung → Schritt „Python-venv“ scheitert; alles andere muss trotzdem laufen.
    prelude = 'echo kaputt > "$HH_BACKUP_DIR"/venv.tar.gz; modify_db; err "pip install fehlgeschlagen"'
    r = _run(env, "migration", prelude=prelude)
    last = _last(r)
    assert last.startswith("HH-UPDATE-ENDE: fehler pip install fehlgeschlagen – Rückweg unvollständig (Python-venv), Sicherung in "), last
    assert _git(env["repo"], "rev-parse", "HEAD") == old, "Code wurde trotzdem zurückgesetzt"
    (d,) = _backups(env)
    assert _meta(d)["STATUS"] == "rueckweg_unvollstaendig" and (d / "sessions.db.zst").is_file()
    assert "systemctl start hydrahive2.service" in _calls(env), "der Dienst wird in jedem Fall gestartet"
    assert "Rückweg-Schritt 'Python-venv' fehlgeschlagen" in r.stdout
    assert d.name in last


def test_e12_ruckweg_beendet_nie_mit_dem_gleichen_status_wie_erfolg(env):
    old, new = _setup(env)
    r = _run(env, "pip", prelude='echo kaputt > "$HH_BACKUP_DIR"/venv.tar.gz; err "x"')
    assert "unvollständig" in _last(r) and "zurückgesetzt" not in _last(r)


# --- Rückweg löscht nie etwas ------------------------------------------------------------------------------------------

def test_rueckweg_loescht_nichts_vorher_vorhandene_dateien_bleiben(env):
    old, new = _setup(env)
    (env["data"] / "wichtig.txt").write_text("daten")
    (env["cfg"] / "extra.conf").write_text("neu")
    (_sysd(env) / "nostart_commits").write_text(new + "\n")
    r = _run(env, "migration")
    assert "zurückgesetzt" in _last(r), r.stdout + r.stderr
    assert (env["data"] / "wichtig.txt").read_text() == "daten"
    k = _kaputt_dir(env)
    tar = subprocess.run(["tar", "-tf", str(k / "etc-hydrahive2-neu.tar")], capture_output=True, text=True).stdout
    assert "hydrahive2/extra.conf" in tar, "der kaputte Config-Stand wird mitgesichert"
    assert (env["cfg"] / "extra.conf").read_text() == "neu", "Zurückspielen löscht nie eine Datei, die es vorher nicht gab"


def test_restore_ueberschreibt_keine_vorhandene_db(tmp_path):
    db = tmp_path / "sessions.db"
    from tests.test_update_safety import _make_db
    _make_db(db)
    snap = tmp_path / "s.zst"
    subprocess.run(["python3", str(SNAP), "snapshot", str(db), str(snap)], check=True, capture_output=True)
    r = subprocess.run(["python3", str(SNAP), "restore", str(snap), str(db)], capture_output=True, text=True)
    assert r.returncode == 2 and "zur Seite gelegt" in r.stderr
    assert db.exists()


def test_restore_folgt_keinem_symlink_und_schreibt_atomar(tmp_path):
    from tests.test_update_safety import _make_db
    src = tmp_path / "quelle.db"
    _make_db(src)
    snap = tmp_path / "s.zst"
    subprocess.run(["python3", str(SNAP), "snapshot", str(src), str(snap)], check=True, capture_output=True)
    ziel_ordner = tmp_path / "daten"
    ziel_ordner.mkdir()
    fremd = tmp_path / "fremd.txt"
    fremd.write_text("geheim")
    (ziel_ordner / "sessions.db.neu").symlink_to(fremd)                           # vorbereiteter Link des Dienstnutzers
    r = subprocess.run(["python3", str(SNAP), "restore", str(snap), str(ziel_ordner / "sessions.db")], capture_output=True, text=True)
    assert r.returncode == 2 and fremd.read_text() == "geheim"
    assert (ziel_ordner / "sessions.db.neu").is_symlink(), "eine fremde Zwischendatei wird nicht gelöscht"
    (ziel_ordner / "sessions.db.neu").unlink()
    ok = subprocess.run(["python3", str(SNAP), "restore", str(snap), str(ziel_ordner / "sessions.db")], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    con = sqlite3.connect(ziel_ordner / "sessions.db")
    assert con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    con.close()
    assert not (ziel_ordner / "sessions.db.neu").exists()


def test_restore_lehnt_defekte_sicherung_ab_und_hinterlaesst_nichts(tmp_path):
    snap = tmp_path / "s.zst"
    snap.write_bytes(b"kein zstd")
    ziel = tmp_path / "d"
    ziel.mkdir()
    r = subprocess.run(["python3", str(SNAP), "restore", str(snap), str(ziel / "sessions.db")], capture_output=True, text=True)
    assert r.returncode == 2 and list(ziel.iterdir()) == []


# --- Abschalter, E13, Health-URL --------------------------------------------------------------------------------------------

def test_rueckweg_laesst_sich_abschalten(env):
    old, new = _setup(env)
    r = _run(env, "pip", rollback=False)
    assert "Automatischer Rückweg abgeschaltet" in r.stdout and "ROLLBACK.txt" in r.stdout
    (d,) = _backups(env)
    assert _meta(d)["STATUS"] == "gesichert"                                       # bleibt für eine Rückweg von Hand


def test_e13_unterbrochenes_update_wird_nur_gemeldet_wenn_der_dienst_laeuft(env):
    old = _git(env["repo"], "rev-parse", "HEAD")
    root = env["tmp"] / "varbackups" / "update"
    root.mkdir(parents=True)
    root.parent.chmod(0o755)
    root.chmod(0o700)
    d = root / "20261101T100000Z_abcdef12"
    d.mkdir()
    (d / "meta.env").write_text(f"STATUS=gesichert\nOLD_COMMIT={old}\nNEW_COMMIT={old}\nRESTARTED=1\nSTART=20261101T100000Z\n")
    r = _run(env, "ok")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Vorheriges Update unterbrochen" in r.stdout
    assert _meta(d)["STATUS"] == "unterbrochen" and not (d / "kaputt").exists()
    assert "HH-UPDATE-WARNUNG: Vorheriges Update unterbrochen" in r.stdout


def test_e13_automatisch_zurueck_nur_wenn_der_neue_stand_nicht_startet(env):
    old, new = _setup(env)
    _git(env["repo"], "pull", "-q", "--ff-only")                                   # das unterbrochene Update hatte schon gepullt
    root = env["tmp"] / "varbackups" / "update"
    root.mkdir(parents=True)
    root.parent.chmod(0o755)
    root.chmod(0o700)
    d = root / "20261101T100000Z_abcdef12"
    d.mkdir()
    (d / "meta.env").write_text(f"STATUS=gesichert\nOLD_COMMIT={old}\nNEW_COMMIT={new}\nRESTARTED=1\nSTART=20261101T100000Z\nDB_BACKED_UP=0\n")
    (_sysd(env) / "bad_health_commits").write_text(new + "\n")
    r = _run(env, "ok", HH_INTERRUPTED_HEALTH_TIMEOUT="1", prelude="true")
    assert "automatischer Rückweg" in r.stdout
    assert (d / "kaputt").is_dir() and _meta(d)["STATUS"] == "zurueckgesetzt"


def test_health_url_liest_port_aus_der_unit_nicht_fest_verdrahtet(env, tmp_path):
    unit = tmp_path / "u.service"
    unit.write_text("[Service]\nEnvironment=HH_HOST=0.0.0.0\nEnvironment=HH_PORT=9123\n")
    script = (f'log() {{ :; }}\nerr() {{ exit 1; }}\nsource "{LIB / "update-safety.sh"}"\nsource "{LIB / "update-check.sh"}"\n'
              'hh_health_url\n')
    base = {"PATH": "/usr/bin:/bin", "HH_UNIT_FILE": str(unit), "HH_DATA_DIR": str(tmp_path), "HH_REPO_DIR": str(tmp_path)}
    r = subprocess.run(["bash", "-c", script], env=base, capture_output=True, text=True)
    assert r.stdout.strip() == "http://127.0.0.1:9123/api/health"
    r = subprocess.run(["bash", "-c", script], env={**base, "HH_PORT": "8002", "HH_HOST": "127.0.0.1"}, capture_output=True, text=True)
    assert r.stdout.strip() == "http://127.0.0.1:8002/api/health"
    r = subprocess.run(["bash", "-c", script], env={**base, "HH_UNIT_FILE": "/nichts"}, capture_output=True, text=True)
    assert r.stdout.strip() == "http://127.0.0.1:8001/api/health"


def test_schlusszeile_bleibt_eine_einzige_zeile_im_format_des_update_fensters(env):
    """frontend/src/shared/_updateLogStatus.ts: ^HH-UPDATE-ENDE: (ok|fehler)(?: (.*))?$ – genau eine, auch nach Rückweg."""
    import re
    old, new = _setup(env)
    r = _run(env, "pip")
    ends = [l for l in r.stdout.splitlines() if l.startswith("HH-UPDATE-ENDE:")]
    assert len(ends) == 1 and re.match(r"^HH-UPDATE-ENDE: (ok|fehler)(?: (.*))?$", ends[0]) and ends[0] == _last(r)


def test_bibliotheken_syntax_und_kopie_im_sicherungsordner(env):
    for f in ("update-check.sh", "update-rollback.sh", "update-safety.sh"):
        assert subprocess.run(["bash", "-n", str(LIB / f)]).returncode == 0
    _setup(env)
    assert _run(env, "ok").returncode == 0
    (d,) = _backups(env)
    for name in ("update-safety.sh", "update-check.sh", "update-rollback.sh", "db_snapshot.py"):
        assert oct((d / name).stat().st_mode & 0o777) == "0o600", name


# --- Probe U4P auf hydratest (23.11.2026): DB-Werkzeug im root-only-Sicherungsordner ---------------------------------

def test_migrationsstand_lesbar_auch_wenn_dbowner_den_sicherungsordner_nicht_lesen_darf(tmp_path):
    """Nach dem Rückweg kommt das DB-Werkzeug aus dem Sicherungsordner (root, 0700). Der Dienstnutzer darf es nicht
    lesen; die Prüfung muss den Migrationsstand trotzdem lesen (Fund der echten Probe, in Attrappen vorher unsichtbar)."""
    bk = tmp_path / "backup"
    bk.mkdir()
    (bk / "db_snapshot.py").write_text(SNAP.read_text())
    db = tmp_path / "sessions.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE schema_version(version INTEGER, applied_at TEXT)")
    con.execute("INSERT INTO schema_version VALUES (66, 'x')")
    con.commit()
    con.close()
    script = f"""
set -euo pipefail
source "{LIB}/update-safety.sh"
source "{LIB}/update-check.sh"
# Dienstnutzer simulieren: jeder Pfad im Sicherungsordner ist für ihn nicht lesbar.
hh_as_dbowner() {{ local a; for a in "$@"; do case "$a" in "{bk}"/*) echo "Permission denied: $a" >&2; return 2 ;; esac; done; "$@"; }}
hh_db_schema_version "{bk}/db_snapshot.py" "{db}"
"""
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "66"
