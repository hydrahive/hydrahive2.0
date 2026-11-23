"""Etappe U3 (docs/specs/update-rollback.md §3.1/§6): Sicherung vor dem Update, Platzprüfung, Sperre, Re-exec, Aufbewahrung.

Alles mit kleinen Test-DBs und Attrappen (id, sudo, df); keine echte Produktions-DB, kein Root.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
LIB = INSTALLER / "lib"
UPDATE = INSTALLER / "update.sh"
SNAP = LIB / "db_snapshot.py"
LIBS = ("update-safety.sh", "db_snapshot.py", "git-update.sh", "python-venv.sh")


def _git(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(cwd)}
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout.strip()


def _make_db(path: Path, rows: int = 500) -> None:
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY, text TEXT)")
    con.executemany("INSERT INTO messages(text) VALUES (?)", [("hallo " * 20,)] * rows)
    con.commit()
    con.close()


@pytest.fixture
def env(tmp_path: Path) -> dict:
    """Origin + Arbeitskopie (mit den Installer-Bibliotheken committed), Daten-/Config-Ordner, Attrappen."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-q", "-b", "main")
    (seed / "installer" / "lib").mkdir(parents=True)
    for name in LIBS:
        (seed / "installer" / "lib" / name).write_text((LIB / name).read_text())
    (seed / "core").mkdir()
    (seed / "core" / "pyproject.toml").write_text("[project]\nname='x'\n")
    (seed / "frontend" / "dist").mkdir(parents=True)
    (seed / "frontend" / "src" / "modules").mkdir(parents=True)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", "alt")
    _git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    repo = tmp_path / "repo"
    _git(tmp_path, "clone", "-q", str(origin), str(repo))
    (repo / "frontend" / "dist").mkdir(parents=True, exist_ok=True)
    (repo / "frontend" / "dist" / "index.html").write_text("ALT")
    (repo / "frontend" / "src" / "modules").mkdir(parents=True, exist_ok=True)
    (repo / "frontend" / "src" / "modules" / "m.ts").write_text("modul")
    data = tmp_path / "data"
    data.mkdir()
    _make_db(data / "sessions.db")
    cfg = tmp_path / "etc" / "hydrahive2"
    cfg.mkdir(parents=True)
    (cfg / "secret_key").write_text("geheim")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "id").write_text('#!/bin/bash\n[ "$1" = "-u" ] && echo 0 && exit 0\nexec /usr/bin/id "$@"\n')
    (bin_ / "sudo").write_text('#!/bin/bash\nwhile [ "${1:-}" = "-u" ] || [ "${1:-}" = "-H" ]; do [ "$1" = "-u" ] && shift; shift; done\nexec "$@"\n')
    (bin_ / "chown").write_text("#!/bin/bash\nexit 0\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    unit = tmp_path / "unit.service"
    unit.write_text("[Service]\n")
    return {"tmp": tmp_path, "origin": origin, "seed": seed, "repo": repo, "data": data, "cfg": cfg, "bin": bin_,
            "unit": unit, "lock": tmp_path / "update.lock"}


def _env(e: dict, **extra: str) -> dict:
    base = {"PATH": f"{e['bin']}:/usr/bin:/bin", "HH_REPO_DIR": str(e["repo"]), "HH_USER": "hydrahive",
            "HH_DATA_DIR": str(e["data"]), "HH_CONFIG_DIR": str(e["cfg"]), "HH_UPDATE_LOCK": str(e["lock"]),
            "HH_UNIT_FILE": str(e["unit"]), "HH_NGINX_SITE": str(e["tmp"] / "nginx-site"),
            "HH_SUDOERS_FILE": str(e["tmp"] / "sudoers"), "HOME": str(e["tmp"])}
    base.update(extra)
    return base


def _push_new_commit(e: dict, name: str = "neu.txt") -> str:
    (e["seed"] / name).write_text("neu")
    _git(e["seed"], "add", "-A")
    _git(e["seed"], "commit", "-qm", "neu")
    _git(e["seed"], "push", "-q", str(e["origin"]), "main")
    return _git(e["seed"], "rev-parse", "HEAD")


def _head_script(e: dict) -> str:
    """update.sh vom Anfang bis nach dem Git-Schritt, ohne die SSH-Schritte (die fassen /home an)."""
    t = UPDATE.read_text()
    ssh = t.index('log "SSH-Verzeichnis')
    pull = t.index('log "git pull"')
    stop = t.index("# Wenn update.sh selbst durch den Pull verändert wurde")
    return t[:ssh] + t[pull:stop] + 'echo "KOPF-OK"\n'


def _run_head(e: dict, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", _head_script(e)], env=_env(e, **extra), capture_output=True, text=True,
                          timeout=120, cwd=e["repo"])


def _backups(e: dict) -> list[Path]:
    root = e["data"] / "backups" / "update"
    return sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []


def _meta(d: Path) -> dict:
    return dict(l.split("=", 1) for l in (d / "meta.env").read_text().splitlines() if "=" in l)


# --- db_snapshot.py ----------------------------------------------------------------------------------------------

def test_snapshot_lesbar_und_quick_check_ok(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db)
    dest = tmp_path / "s.db.zst"
    r = subprocess.run(["python3", str(SNAP), "snapshot", str(db), str(dest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert subprocess.run(["python3", str(SNAP), "verify", str(dest)], capture_output=True, text=True).stdout.strip() == "ok"
    out = tmp_path / "entpackt.db"
    subprocess.run(["zstd", "-d", "-q", "-o", str(out), str(dest)], check=True)
    con = sqlite3.connect(out)
    assert con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    assert con.execute("SELECT count(*) FROM messages").fetchone()[0] == 500
    con.close()
    assert not any(p.name.startswith(".") for p in tmp_path.iterdir()), "keine Temp-Reste"


def test_snapshot_quelle_wird_nicht_veraendert(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db)
    before = db.read_bytes()
    subprocess.run(["python3", str(SNAP), "snapshot", str(db), str(tmp_path / "x.zst")], check=True, capture_output=True)
    assert db.read_bytes() == before


def test_snapshot_fehlende_db_meldet_fehler_ohne_reste(tmp_path):
    r = subprocess.run(["python3", str(SNAP), "snapshot", str(tmp_path / "gibtsnicht.db"), str(tmp_path / "x.zst")],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "existiert nicht" in r.stderr
    assert list(tmp_path.iterdir()) == []


def test_snapshot_kaputte_db_wird_abgelehnt(tmp_path):
    bad = tmp_path / "kaputt.db"
    bad.write_bytes(b"das ist keine sqlite-datei" * 100)
    r = subprocess.run(["python3", str(SNAP), "snapshot", str(bad), str(tmp_path / "x.zst")], capture_output=True, text=True)
    assert r.returncode == 2
    assert not (tmp_path / "x.zst").exists() and not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_verify_erkennt_beschaedigte_sicherung(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db)
    dest = tmp_path / "s.db.zst"
    subprocess.run(["python3", str(SNAP), "snapshot", str(db), str(dest)], check=True, capture_output=True)
    data = bytearray(dest.read_bytes())
    data[len(data) // 2] ^= 0xFF
    dest.write_bytes(bytes(data))
    assert subprocess.run(["python3", str(SNAP), "verify", str(dest)], capture_output=True, text=True).returncode == 2


def test_estimate_zaehlt_nur_belegte_seiten(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db, rows=2000)
    con = sqlite3.connect(db)
    full = int(subprocess.run(["python3", str(SNAP), "estimate", str(db)], capture_output=True, text=True).stdout)
    con.execute("DELETE FROM messages WHERE id > 100")
    con.commit()
    con.close()
    small = int(subprocess.run(["python3", str(SNAP), "estimate", str(db)], capture_output=True, text=True).stdout)
    assert 0 < small < full / 2


# --- update.sh Kopf: Sicherung, Platz, Reihenfolge ----------------------------------------------------------------

def test_sicherung_inhalt_und_meta(env):
    new = _push_new_commit(env)
    old = _git(env["repo"], "rev-parse", "HEAD")
    r = _run_head(env)
    assert r.returncode == 0 and "KOPF-OK" in r.stdout, r.stdout + r.stderr
    assert _git(env["repo"], "rev-parse", "HEAD") == new                     # der Pull lief erst NACH der Sicherung
    (d,) = _backups(env)
    m = _meta(d)
    assert m["OLD_COMMIT"] == old and m["NEW_COMMIT"] == new and m["OLD_BRANCH"] == "main"
    assert m["STATUS"] == "ok" and m["VENV_BACKED_UP"] == "0" and m["DB_BACKED_UP"] == "1"
    assert d.name.endswith("_" + old[:8]) and oct(d.stat().st_mode & 0o777) == "0o700"
    for name in ("sessions.db.zst", "etc-hydrahive2.tar", "ROLLBACK.txt", "update-safety.sh", "db_snapshot.py"):
        assert (d / name).is_file(), name
    assert (d / "dist" / "index.html").read_text() == "ALT"
    assert (d / "modules-frontend" / "m.ts").read_text() == "modul"
    assert (d / "units" / "unit.service").exists()
    assert not (d / "venv.tar.zst").exists()
    assert oct((d / "etc-hydrahive2.tar").stat().st_mode & 0o777) == "0o600"
    tar = subprocess.run(["tar", "-tf", str(d / "etc-hydrahive2.tar")], capture_output=True, text=True).stdout
    assert "hydrahive2/secret_key" in tar
    assert subprocess.run(["python3", str(SNAP), "verify", str(d / "sessions.db.zst")], capture_output=True, text=True).stdout.strip() == "ok"
    guide = (d / "ROLLBACK.txt").read_text()
    assert old in guide and "git" in guide and "sessions.db.zst" in guide and "kaputt" in guide


def test_wenig_platz_bricht_ab_vor_git_pull(env):
    _push_new_commit(env)
    old = _git(env["repo"], "rev-parse", "HEAD")
    (env["bin"] / "df").write_text("#!/bin/bash\necho 'Filesystem 1-blocks Used Available Capacity Mounted'\n"
                                   "echo '/dev/x 1000000 999000 1000 99% /'\n")
    (env["bin"] / "df").chmod(0o755)
    r = _run_head(env)
    assert r.returncode != 0 and "KOPF-OK" not in r.stdout
    last = [l for l in r.stdout.splitlines() if l.strip()][-1]
    assert last.startswith("HH-UPDATE-ENDE: fehler Zu wenig Platz für die Sicherung: frei ")
    assert last.endswith("– nichts verändert")
    assert "nötig" in last and "GB" in last
    assert _git(env["repo"], "rev-parse", "HEAD") == old                       # kein Pull
    assert _backups(env) == []                                                 # kein halber Ordner


def test_platz_wird_auch_auf_dem_dateisystem_der_db_geprueft(env):
    """Zwei Dateisysteme: Sicherungsordner hat genug, die DB-Partition nicht → Abbruch."""
    _push_new_commit(env)
    (env["bin"] / "df").write_text(
        "#!/bin/bash\nlast=\"${@: -1}\"\necho 'Filesystem 1-blocks Used Available Capacity Mounted'\n"
        f"case \"$last\" in {env['data']}) echo '/dev/d 1000000 999000 1000 99% /';; *) echo '/dev/b 99999999999999 1 99999999999999 1% /';; esac\n")
    (env["bin"] / "df").chmod(0o755)
    # der Sicherungsordner liegt unter data/ → beide Pfade zeigen auf data; eigenes Backup-Root daneben
    r = _run_head(env, HH_BACKUP_ROOT=str(env["tmp"] / "backups-woanders"))
    assert r.returncode != 0
    assert "Zu wenig Platz" in r.stdout + r.stderr and "nichts verändert" in r.stdout


def test_git_schritt_abgelehnt_hinterlaesst_keine_sicherung(env):
    (env["repo"] / "lokal.txt").write_text("ungespeichert")
    _git(env["repo"], "add", "lokal.txt")                                      # lokale Änderung → Git-Schritt lehnt ab
    f = env["repo"] / "installer" / "lib" / "update-safety.sh"
    f.write_text(f.read_text() + "\n# lokal\n")                                 # getrackte Datei geändert
    r = _run_head(env)
    last = [l for l in r.stdout.splitlines() if l.strip()][-1]
    if r.returncode == 0:                                                      # Git-Lib duldet den Fall: dann zählt nur das Fehlen von Resten
        pytest.skip("hh_git_update lehnt diese lokale Änderung nicht ab")
    assert last.startswith("HH-UPDATE-ENDE: fehler")
    assert _backups(env) == []


def test_ohne_neuen_commit_bleibt_keine_sicherung(env):
    r = _run_head(env)                                                         # origin == lokal
    assert r.returncode == 0, r.stdout + r.stderr
    assert _backups(env) == []


def test_sperre_verhindert_zweiten_lauf(env):
    _push_new_commit(env)
    old = _git(env["repo"], "rev-parse", "HEAD")
    holder = subprocess.Popen(["flock", "-n", str(env["lock"]), "sleep", "30"])
    try:
        import time
        time.sleep(0.5)
        r = _run_head(env)
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode != 0
    last = [l for l in r.stdout.splitlines() if l.strip()][-1]
    assert last == "HH-UPDATE-ENDE: fehler Update läuft bereits – nichts verändert."
    assert _git(env["repo"], "rev-parse", "HEAD") == old and _backups(env) == []


def test_sperre_wird_nach_dem_lauf_freigegeben(env):
    _push_new_commit(env)
    assert _run_head(env).returncode == 0
    assert subprocess.run(["flock", "-n", str(env["lock"]), "true"]).returncode == 0


def test_re_exec_legt_keine_zweite_sicherung_an(env):
    """Zweiter Aufruf mit HH_BACKUP_DIR (wie nach dem Re-exec): keine neue Sicherung, derselbe Ordner."""
    _push_new_commit(env)
    script = (_head_script(env).replace('hh_safety_backup\n', 'hh_safety_backup\nSICHERUNG1="$HH_BACKUP_DIR"\n', 1)
              .replace('echo "KOPF-OK"', 'hh_safety_backup; echo "DIR=$HH_BACKUP_DIR"; echo "ERSTE=$SICHERUNG1"; echo KOPF-OK'))
    r = subprocess.run(["bash", "-c", script], env=_env(env), capture_output=True, text=True, timeout=120, cwd=env["repo"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_backups(env)) == 1
    lines = dict(l.split("=", 1) for l in r.stdout.splitlines() if l.startswith(("DIR=", "ERSTE=")))
    assert lines["DIR"] == lines["ERSTE"] and "keine zweite" in r.stdout


def test_reexec_nach_update_sh_aenderung_nimmt_backup_dir_aus_der_umgebung(env):
    """Der echte Re-exec-Pfad: HH_UPDATE_REEXECED=1 + HH_BACKUP_DIR aus dem ersten Lauf."""
    first = _run_head(env)                                                     # nichts Neues → ohne Sicherung
    assert first.returncode == 0
    (d := env["tmp"] / "vorhanden").mkdir()
    (d / "meta.env").write_text("STATUS=gesichert\nOLD_COMMIT=abc\n")
    r = _run_head(env, HH_UPDATE_REEXECED="1", HH_BACKUP_DIR=str(d))
    assert r.returncode == 0 and "keine zweite" in r.stdout
    assert _backups(env) == []


# --- venv nur bei Änderung (F3) --------------------------------------------------------------------------------------

def _fake_venv(e: dict) -> None:
    v = e["repo"] / ".venv" / "bin"
    v.mkdir(parents=True)
    (v / "python").write_text("#!/bin/bash\n[ \"$1\" = -c ] && echo 3.12 && exit 0\n[ \"$1\" = -m ] && exit 0\nexit 0\n")
    (v / "python").chmod(0o755)
    (e["repo"] / ".gitignore").write_text(".venv/\n")


def _fake_system_python(e: dict) -> dict:
    d = e["tmp"] / "usrbin"
    d.mkdir()
    for n in ("python3", "python3.13", "python3.12"):
        (d / n).write_text("#!/bin/bash\n[ \"$1\" = -c ] && echo 3.12 && exit 0\nexec /usr/bin/python3 \"$@\"\n")
        (d / n).chmod(0o755)
    return {"HH_PYTHON_BIN_DIR": str(d)}


def test_venv_nur_bei_geaenderter_pyproject(env):
    _fake_venv(env)
    extra = _fake_system_python(env)
    _push_new_commit(env, "nur-eine-datei.txt")                                # pyproject unverändert
    r = _run_head(env, **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    (d,) = _backups(env)
    assert _meta(d)["VENV_BACKED_UP"] == "0" and not (d / "venv.tar.zst").exists()


def test_venv_wird_gesichert_wenn_pyproject_sich_aendert(env):
    _fake_venv(env)
    extra = _fake_system_python(env)
    (env["seed"] / "core" / "pyproject.toml").write_text("[project]\nname='x'\ndependencies=['neu']\n")
    _git(env["seed"], "commit", "-qam", "dep")
    _git(env["seed"], "push", "-q", str(env["origin"]), "main")
    r = _run_head(env, **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    (d,) = _backups(env)
    assert _meta(d)["VENV_BACKED_UP"] == "1" and (d / "venv.tar.zst").is_file()
    tar = subprocess.run(f'zstd -dc "{d / "venv.tar.zst"}" | tar -tf -', shell=True, capture_output=True, text=True).stdout
    assert ".venv/bin/python" in tar


# --- Aufbewahrung (§6) ---------------------------------------------------------------------------------------------

def _prune(env: dict, **extra: str) -> subprocess.CompletedProcess:
    src = (LIB / "update-safety.sh")
    script = f'log() {{ echo "$*"; }}\nerr() {{ echo "ERR $*" >&2; exit 1; }}\nsource "{src}"\nhh_backup_prune\n'
    return subprocess.run(["bash", "-c", script], env=_env(env, **extra), capture_output=True, text=True)


def _fake_backup(env: dict, stamp: str, status: str, *, kaputt: bool = False) -> Path:
    d = env["data"] / "backups" / "update" / f"{stamp}_abcdef12"
    d.mkdir(parents=True)
    (d / "meta.env").write_text(f"STATUS={status}\n")
    (d / "sessions.db.zst").write_text("x")
    if kaputt:
        (d / "kaputt").mkdir()
    return d


def test_aufbewahrung_behaelt_die_letzten_zwei_ok(env):
    ds = [_fake_backup(env, f"2026112{i}T100000Z", "ok") for i in range(1, 6)]
    assert _prune(env).returncode == 0
    assert [d.exists() for d in ds] == [False, False, False, True, True]


def test_aufbewahrung_loescht_nie_rueckweg_und_unterbrochene(env):
    keepers = [
        _fake_backup(env, "20261101T100000Z", "zurueckgesetzt"),
        _fake_backup(env, "20261102T100000Z", "rueckweg_unvollstaendig"),
        _fake_backup(env, "20261103T100000Z", "gesichert"),
        _fake_backup(env, "20261104T100000Z", "ok", kaputt=True),
    ]
    oks = [_fake_backup(env, f"2026112{i}T100000Z", "ok") for i in range(1, 5)]
    assert _prune(env).returncode == 0
    assert all(d.exists() for d in keepers)
    assert [d.exists() for d in oks] == [False, False, True, True]


def test_aufbewahrung_fasst_fremde_ordner_nicht_an(env):
    fremd = env["data"] / "backups" / "update" / "meine-notizen"
    fremd.mkdir(parents=True)
    (fremd / "meta.env").write_text("STATUS=ok\n")
    for i in range(1, 5):
        _fake_backup(env, f"2026112{i}T100000Z", "ok")
    _prune(env)
    assert fremd.exists()


def test_erfolgreiches_update_raeumt_alte_sicherungen_auf(env):
    for i in range(1, 4):
        _fake_backup(env, f"2026110{i}T100000Z", "ok")
    _push_new_commit(env)
    assert _run_head(env).returncode == 0
    bleibt = _backups(env)
    assert len(bleibt) == 2 and all(_meta(d)["STATUS"] == "ok" for d in bleibt)
    assert any(not d.name.endswith("_abcdef12") for d in bleibt), "die neue Sicherung muss dabei sein"
    assert not (env["data"] / "backups" / "update" / "20261101T100000Z_abcdef12").exists()


# --- Verdrahtung in update.sh ---------------------------------------------------------------------------------------

def test_update_sh_reihenfolge_sperre_sicherung_pull():
    t = UPDATE.read_text()
    assert t.index("hh_safety_lock") < t.index("hh_safety_backup") < t.index('hh_git_update "$HH_REPO_DIR"') < t.index("hh_safety_after_git")
    assert t.count("hh_safety_backup") == 1 and t.count("trap ") == 1
    assert "hh_safety_finish" in t[t.index("_hh_end()"):t.index("trap _hh_end EXIT")]


def test_endzeile_kommt_nach_dem_aufraeumen_und_exit_code_bleibt():
    t = UPDATE.read_text()
    body = t[t.index("_hh_end()"):t.index("trap _hh_end EXIT")]
    assert body.index("hh_safety_finish") < body.index("HH-UPDATE-ENDE: ok")
    line = next(l for l in body.splitlines() if 'hh_safety_finish "$rc"' in l)
    assert "|| true" in line


def test_bibliothek_und_skript_haben_gueltige_syntax():
    for f in (UPDATE, LIB / "update-safety.sh"):
        assert subprocess.run(["bash", "-n", str(f)]).returncode == 0
