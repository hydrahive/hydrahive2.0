"""Migrationen laufen atomar (Probe U4P auf hydratest, 23.11.2026).

Befund: Eine Migration, die mitten drin scheitert (erst CREATE TABLE, dann Fehler), ließ die Tabelle stehen. Der nächste
Start bekam „table … already exists“, wertete das als „bereits partiell angewendet“ und trug die Version ein – eine
kaputte Migration galt als erfolgreich. Jetzt: Datei + Versionszeile in einer Transaktion, bei Fehler Rollback.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hydrahive.db import migrations as core_mig

KAPUTT = "CREATE TABLE u4p_probe (id INTEGER PRIMARY KEY);\nINSERT INTO tabelle_gibt_es_nicht VALUES (1);\n"


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _versions(conn: sqlite3.Connection) -> list[int]:
    return [r[0] for r in conn.execute("SELECT version FROM schema_version ORDER BY version")]


@pytest.fixture
def mdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "migrations"
    d.mkdir()
    monkeypatch.setattr(core_mig, "MIGRATIONS_DIR", d)
    return d


def test_kaputte_migration_hinterlaesst_nichts_und_bleibt_beim_zweiten_start_kaputt(mdir: Path, tmp_path: Path):
    (mdir / "001_ok.sql").write_text("CREATE TABLE t1 (id INTEGER);")
    (mdir / "002_kaputt.sql").write_text(KAPUTT)
    conn = sqlite3.connect(tmp_path / "s.db")
    with pytest.raises(sqlite3.OperationalError, match="tabelle_gibt_es_nicht"):
        core_mig.apply_migrations(conn)
    assert "u4p_probe" not in _tables(conn), "halber Stand zurückgerollt"
    assert _versions(conn) == [1], "nur die gute Migration verbucht"
    assert not conn.in_transaction
    # zweiter Start (früher: „already exists“ → als erledigt verbucht)
    with pytest.raises(sqlite3.OperationalError, match="tabelle_gibt_es_nicht"):
        core_mig.apply_migrations(conn)
    assert _versions(conn) == [1] and "u4p_probe" not in _tables(conn)


def test_erfolg_verbucht_objekte_und_version_gemeinsam(mdir: Path, tmp_path: Path):
    (mdir / "001_a.sql").write_text("CREATE TABLE a (x);\nINSERT INTO a VALUES (1);")
    conn = sqlite3.connect(tmp_path / "s.db")
    core_mig.apply_migrations(conn)
    conn.close()
    conn = sqlite3.connect(tmp_path / "s.db")                 # wirklich festgeschrieben?
    assert _versions(conn) == [1] and conn.execute("SELECT COUNT(*) FROM a").fetchone()[0] == 1


def test_trigger_rumpf_mit_begin_end_wird_umhuellt_und_rollt_zurueck(mdir: Path, tmp_path: Path):
    """„BEGIN … END;“ eines Triggers ist keine eigene Transaktionssteuerung – die Datei bleibt atomar."""
    (mdir / "001_trg.sql").write_text(
        "CREATE TABLE t (x);\n"
        "CREATE TRIGGER t_ai AFTER INSERT ON t\nBEGIN\n  SELECT 1;\nEND;\n"
        "INSERT INTO gibt_es_nicht VALUES (1);\n"
    )
    conn = sqlite3.connect(tmp_path / "s.db")
    with pytest.raises(sqlite3.OperationalError):
        core_mig.apply_migrations(conn)
    assert "t" not in _tables(conn)


def test_datei_mit_eigener_transaktion_laeuft_wie_bisher(mdir: Path, tmp_path: Path):
    (mdir / "001_eigen.sql").write_text("BEGIN;\nCREATE TABLE e (x);\nCOMMIT;\n")
    conn = sqlite3.connect(tmp_path / "s.db")
    core_mig.apply_migrations(conn)
    assert "e" in _tables(conn) and _versions(conn) == [1]


def test_pragma_datei_laeuft_ohne_huelle(mdir: Path, tmp_path: Path):
    """PRAGMA foreign_keys=OFF wirkt in einer Transaktion nicht (DROP TABLE würde per CASCADE löschen) – solche
    Dateien (haushaltsbuch 009/010) laufen deshalb ohne äußere Transaktion."""
    (mdir / "001_p.sql").write_text(
        "CREATE TABLE p (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE k (pid REFERENCES p(id) ON DELETE CASCADE);\n"
        "INSERT INTO p VALUES (1); INSERT INTO k VALUES (1);\n"
    )
    (mdir / "002_umbau.sql").write_text(
        "PRAGMA foreign_keys = OFF;\nDROP TABLE p;\nCREATE TABLE p (id INTEGER PRIMARY KEY);\nPRAGMA foreign_keys = ON;\n"
    )
    conn = sqlite3.connect(tmp_path / "s.db")
    conn.execute("PRAGMA foreign_keys = ON")
    core_mig.apply_migrations(conn)
    assert conn.execute("SELECT COUNT(*) FROM k").fetchone()[0] == 1, "keine Kaskade"


def test_objekt_ausserhalb_der_migration_angelegt_gilt_weiter_als_vorhanden(mdir: Path, tmp_path: Path):
    conn = sqlite3.connect(tmp_path / "s.db")
    conn.execute("CREATE TABLE schon_da (x)")
    conn.commit()
    (mdir / "001_da.sql").write_text("CREATE TABLE schon_da (x);")
    core_mig.apply_migrations(conn)
    assert _versions(conn) == [1]


def test_echte_kern_migrationen_frisch_und_zweiter_lauf(tmp_path: Path):
    conn = sqlite3.connect(tmp_path / "s.db")
    core_mig.apply_migrations(conn)
    n = len(_versions(conn))
    assert n == len(list(core_mig.MIGRATIONS_DIR.glob("*.sql")))
    core_mig.apply_migrations(conn)
    assert len(_versions(conn)) == n


def test_modul_migration_kaputt_hinterlaesst_nichts(mod_env):
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    m = mod_env / "m"
    m.mkdir()
    (m / "001_ok.sql").write_text("CREATE TABLE module_z_ok (x);")
    (m / "002_kaputt.sql").write_text(KAPUTT.replace("u4p_probe", "module_z_probe"))
    for _ in range(2):                                         # zweiter Lauf = nächster Start
        with pytest.raises(sqlite3.OperationalError, match="tabelle_gibt_es_nicht"):
            apply_module_migrations("z", m)
    with db() as c:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        vers = [r[0] for r in c.execute("SELECT version FROM module_schema_version WHERE module_id='z'")]
    assert "module_z_probe" not in tabs and "module_z_ok" in tabs
    assert vers == [1]


# --- Review #774 (hydrahive-reviewer): Befunde 1–5 ---------------------------------------------------------------

def _conn(tmp_path: Path, fk: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(tmp_path / "x.db")
    if fk:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _record(conn: sqlite3.Connection):
    return lambda: conn.execute("CREATE TABLE IF NOT EXISTS vermerk (n)")


@pytest.mark.parametrize("sql,ohne_huelle", [
    ("SELECT 1; PRAGMA user_version=3;", True),                                   # PRAGMA mitten in der Zeile (Fund 3)
    ("select 1;\n  vacuum;", True),                                              # Kleinschreibung
    ("-- Kommentar\n\nBEGIN IMMEDIATE;\nSELECT 1;", True),                       # eigene Transaktion nach Kommentar
    ("begin transaction;\nselect 1;\ncommit;", True),
    ("ATTACH DATABASE 'x.db' AS x;", True),
    ("CREATE TABLE t (a);\nCOMMIT;", True),
    ("CREATE TRIGGER t AFTER INSERT ON a BEGIN INSERT INTO b VALUES (1); END;", False),   # Trigger-Rumpf ≠ Transaktion
    ("CREATE TRIGGER t AFTER INSERT ON a\nBEGIN\n  INSERT INTO b VALUES (1);\nEND;", False),
    ("PRAGMA foreign_keys=OFF;\nCREATE TABLE t (a);", False),                    # wird von run_migration_script selbst behandelt
    ("CREATE TABLE t (beginn TEXT, attached_at TEXT);", False),                   # Wortteile lösen keinen Fehlalarm aus
    ("INSERT INTO t VALUES ('wir fangen an');", False),
])
def test_regex_not_wrappable_tabelle(sql: str, ohne_huelle: bool):
    assert bool(core_mig._NOT_WRAPPABLE.search(sql)) is ohne_huelle


def test_already_exists_mitten_in_der_datei_wendet_den_rest_an_und_haelt_alles_atomar(tmp_path: Path):
    """Fund 1: früher blieb 'neu' stehen, 'danach' fehlte, und die Version war verbucht (halber Stand)."""
    conn = _conn(tmp_path)
    conn.execute("CREATE TABLE vorhanden (a)")
    core_mig.run_migration_script(
        conn, "CREATE TABLE neu (a);\nCREATE TABLE vorhanden (a);\nCREATE TABLE danach (a);\n", "t", _record(conn))
    assert {"neu", "danach", "vorhanden", "vermerk"} <= _tables(conn)
    assert not conn.in_transaction


def test_already_exists_und_danach_ein_echter_fehler_rollt_alles_zurueck(tmp_path: Path):
    conn = _conn(tmp_path)
    conn.execute("CREATE TABLE vorhanden (a)")
    with pytest.raises(sqlite3.OperationalError, match="gibt_es_nicht"):
        core_mig.run_migration_script(
            conn, "CREATE TABLE neu (a);\nCREATE TABLE vorhanden (a);\nINSERT INTO gibt_es_nicht VALUES (1);\n", "t", _record(conn))
    assert "neu" not in _tables(conn) and "vermerk" not in _tables(conn)
    assert not conn.in_transaction


def test_duplicate_column_wird_uebersprungen_der_rest_angewendet(tmp_path: Path):
    conn = _conn(tmp_path)
    conn.execute("CREATE TABLE t (a, b)")
    core_mig.run_migration_script(
        conn, "ALTER TABLE t ADD COLUMN b;\nALTER TABLE t ADD COLUMN c;\n", "t", _record(conn))
    assert [r[1] for r in conn.execute("PRAGMA table_info(t)")] == ["a", "b", "c"]


@pytest.mark.parametrize("exc", [ValueError, KeyboardInterrupt, sqlite3.IntegrityError])
def test_record_wirft_rollback_und_keine_offene_transaktion(tmp_path: Path, exc):
    """Fund 2: wirft record(), bleibt nichts Halbes und keine offene Transaktion zurück."""
    conn = _conn(tmp_path)

    def boom():
        raise exc("record")

    with pytest.raises(exc):
        core_mig.run_migration_script(conn, "CREATE TABLE a (x);", "t", boom)
    assert not conn.in_transaction and "a" not in _tables(conn)


def test_integrity_error_in_der_datei_rollt_zurueck(tmp_path: Path):
    conn = _conn(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        core_mig.run_migration_script(
            conn, "CREATE TABLE u (id INTEGER PRIMARY KEY);\nINSERT INTO u VALUES (1);\nINSERT INTO u VALUES (1);\n",
            "t", _record(conn))
    assert "u" not in _tables(conn) and not conn.in_transaction


KINDER = ("CREATE TABLE p (id INTEGER PRIMARY KEY);\n"
          "CREATE TABLE k (id INTEGER PRIMARY KEY, p INTEGER REFERENCES p(id) ON DELETE CASCADE);\n"
          "INSERT INTO p VALUES (1);\nINSERT INTO k VALUES (1, 1);\n")


def test_tabelle_neu_aufbauen_fehler_mittendrin_verliert_keine_daten(tmp_path: Path):
    """Fund 4 (haushaltsbuch-Muster): PRAGMA foreign_keys=OFF + DROP TABLE; scheitert die Datei danach, ist alles
    zurückgerollt (vorher: Daten nur noch in der Zwischentabelle, beim zweiten Lauf gelöscht)."""
    conn = _conn(tmp_path)
    conn.executescript(KINDER)
    sql = ("PRAGMA foreign_keys=OFF;\nCREATE TABLE p_neu (id INTEGER PRIMARY KEY);\nINSERT INTO p_neu SELECT id FROM p;\n"
           "DROP TABLE p;\nALTER TABLE gibt_es_nicht RENAME TO y;\n")
    for _ in range(2):                                                         # auch beim zweiten Start
        with pytest.raises(sqlite3.OperationalError, match="gibt_es_nicht"):
            core_mig.run_migration_script(conn, sql, "t", _record(conn))
        assert conn.execute("SELECT count(*) FROM p").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM k").fetchone()[0] == 1
        assert "p_neu" not in _tables(conn) and not conn.in_transaction
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "Fremdschlüssel wieder an"


def test_tabelle_neu_aufbauen_erfolg_kaskadiert_nicht(tmp_path: Path):
    conn = _conn(tmp_path)
    conn.executescript(KINDER)
    sql = ("PRAGMA foreign_keys=OFF;\nCREATE TABLE p_neu (id INTEGER PRIMARY KEY);\nINSERT INTO p_neu SELECT id FROM p;\n"
           "DROP TABLE p;\nALTER TABLE p_neu RENAME TO p;\nPRAGMA foreign_keys=ON;\n")
    core_mig.run_migration_script(conn, sql, "t", _record(conn))
    assert conn.execute("SELECT count(*) FROM p").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM k").fetchone()[0] == 1, "ON DELETE CASCADE darf Kindzeilen nicht löschen"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1 and not conn.in_transaction


def test_pragma_mitten_in_der_datei_bekommt_keine_huelle(tmp_path: Path):
    conn = _conn(tmp_path)
    conn.executescript(KINDER)
    sql = "SELECT 1;\nPRAGMA user_version=7;\nCREATE TABLE z (a);\n"
    assert core_mig._NOT_WRAPPABLE.search(sql)
    core_mig.run_migration_script(conn, sql, "t", _record(conn))
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 7              # das PRAGMA wirkt (in einer Transaktion täte es das nicht für foreign_keys)


def test_aufrufer_mit_offener_transaktion_wird_nicht_mitgerissen(tmp_path: Path):
    conn = _conn(tmp_path)
    conn.execute("CREATE TABLE vorher (a)")
    conn.execute("INSERT INTO vorher VALUES (1)")                              # offen
    core_mig.run_migration_script(conn, "CREATE TABLE b (x);", "t", _record(conn))
    assert not conn.in_transaction and conn.execute("SELECT count(*) FROM vorher").fetchone()[0] == 1
