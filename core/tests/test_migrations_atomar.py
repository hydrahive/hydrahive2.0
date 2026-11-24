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
