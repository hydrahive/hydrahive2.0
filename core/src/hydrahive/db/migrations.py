from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Callable
from pathlib import Path

from hydrahive.db._utils import now_iso

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Läuft ohne äußere Transaktion wie bisher: Dateien mit eigener Transaktionssteuerung (BEGIN/COMMIT/ROLLBACK, z. B. Kern
# 062/064/065) und Anweisungen, die in einer Transaktion nicht erlaubt sind oder nicht wirken (VACUUM, ATTACH, DETACH,
# PRAGMAs außer foreign_keys). BEGIN/COMMIT/ROLLBACK zählen nur am Zeilenanfang; Trigger-Rümpfe („BEGIN" ohne direktes
# „;") zählen nicht. Die Schlüsselwörter werden an jeder Stelle der Datei gesucht (nicht nur am Anfang): ein Treffer in
# einem Kommentar lässt die Datei höchstens ohne Hülle laufen, also wie früher – das ist der sichere Fehlalarm.
# PRAGMA foreign_keys behandelt run_migration_script selbst (siehe dort).
_NOT_WRAPPABLE = re.compile(
    r"^\s*(?:BEGIN|COMMIT|ROLLBACK)(?:\s+(?:DEFERRED|IMMEDIATE|EXCLUSIVE))?(?:\s+TRANSACTION)?\s*;"
    r"|\b(?:PRAGMA\s+(?!foreign_keys\b)\w+|VACUUM|ATTACH|DETACH)\b",
    re.IGNORECASE | re.MULTILINE,
)
_EXISTS = ("duplicate column name", "already exists")
_FK_OFF = re.compile(r"^\s*PRAGMA\s+foreign_keys\s*=\s*(?:OFF|0|FALSE|NO)\s*;", re.IGNORECASE | re.MULTILINE)


def _statements(sql: str) -> list[str]:
    """Teilt ein Skript in einzelne Anweisungen (Trigger-Rümpfe bleiben ganz, dafür sorgt complete_statement)."""
    out: list[str] = []
    buf = ""
    for part in sql.split(";"):
        buf += part + ";"
        if sqlite3.complete_statement(buf):
            out.append(buf)
            buf = ""
    rest = buf.rstrip(";")
    if rest.strip():
        out.append(rest)
    return [x for x in out if x.strip().strip(";").strip()]


def _run_tolerant(conn: sqlite3.Connection, sql: str, label: str) -> None:
    """Nach „already exists"/„duplicate column name“: dieselbe Datei Anweisung für Anweisung, vorhandene Objekte werden
    übersprungen, alles andere wird angewendet – in EINER Transaktion, ein anderer Fehler rollt alles zurück."""
    conn.execute("BEGIN")
    for stmt in _statements(sql):
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as exc:
            if not any(m in str(exc) for m in _EXISTS):
                raise
            logger.warning("Migration %s: bereits vorhanden (%s) — Anweisung übersprungen", label, exc)


def run_migration_script(conn: sqlite3.Connection, sql: str, label: str, record: Callable[[], None]) -> None:
    """Führt eine Migrations-Datei aus und verbucht sie über ``record`` (Versionszeile), dann COMMIT.

    Atomar: Ohne eigene Transaktionssteuerung läuft die Datei samt Versionszeile in EINER Transaktion. Scheitert
    sie – auch durch einen anderen Fehler als SQL (Ctrl-C, ``record`` wirft) –, wird alles zurückgerollt und der Fehler
    weitergereicht. Es bleibt kein halber Stand zurück, den ein späterer Start als „bereits angewendet“ verbuchen
    könnte (Probe U4P, 23.11.2026).

    „already exists“/„duplicate column name“ (Objekt außerhalb der Migration angelegt, Alt-DB): Die Datei läuft dann
    Anweisung für Anweisung ohne die vorhandenen Objekte (``_run_tolerant``), ebenfalls in einer Transaktion.

    Fremdschlüssel: Verlangt die Datei ``PRAGMA foreign_keys=OFF`` (Tabelle neu aufbauen: ``DROP TABLE`` würde sonst per
    ON DELETE CASCADE Kindzeilen löschen), wirkt das innerhalb einer Transaktion nicht. Deshalb schaltet diese Funktion
    sie in genau diesem Fall VOR der Transaktion auf der Verbindung ab und danach wieder ein; so rollt ein Fehler
    mittendrin vollständig zurück (vorher: Daten nur noch in der Zwischentabelle, beim zweiten Lauf gelöscht).
    Verstöße danach werden gemeldet (kein Abbruch: Alt-DBs können welche haben). Alle anderen Dateien laufen mit der
    Fremdschlüssel-Einstellung der Verbindung wie bisher.
    """
    wrapped = not _NOT_WRAPPABLE.search(sql)
    fk_was_on = False
    if wrapped:
        conn.commit()                       # nichts Offenes mitnehmen (executescript hätte es ohnehin festgeschrieben)
        if _FK_OFF.search(sql):
            fk_was_on = bool(conn.execute("PRAGMA foreign_keys").fetchone()[0])
            if fk_was_on:
                conn.execute("PRAGMA foreign_keys=OFF")
    try:
        try:
            conn.executescript(("BEGIN;\n" + sql) if wrapped else sql)
        except sqlite3.OperationalError as exc:
            if not any(m in str(exc) for m in _EXISTS):
                raise
            if not wrapped:
                # Eigene Transaktionssteuerung (BEGIN;/COMMIT; in der Datei, z. B. 062): nicht Anweisung für Anweisung
                # nachfahren (verschachteltes BEGIN) – Verhalten wie bisher: als vorhanden werten.
                logger.warning("Migration %s bereits partiell angewendet (%s) — überspringe", label, exc)
            else:
                if conn.in_transaction:
                    conn.rollback()         # den halben Versuch verwerfen
                logger.warning("Migration %s: Objekt schon vorhanden (%s) — wende die Datei Anweisung für Anweisung an", label, exc)
                _run_tolerant(conn, sql, label)
        if fk_was_on:
            bad = conn.execute("PRAGMA foreign_key_check").fetchall()
            if bad:
                logger.warning("Migration %s: %d Fremdschlüssel-Verstöße in der Datenbank (nicht durch diese Migration geprüft)", label, len(bad))
        record()
        conn.commit()
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        if fk_was_on:
            conn.execute("PRAGMA foreign_keys=ON")


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_version (
               version    INTEGER PRIMARY KEY,
               applied_at TEXT NOT NULL
           )"""
    )


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_version_table(conn)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return (row[0] if row else 0) or 0


def apply_migrations(conn: sqlite3.Connection) -> None:
    current = current_version(conn)
    if not MIGRATIONS_DIR.exists():
        logger.warning("Keine Migrations gefunden in %s", MIGRATIONS_DIR)
        return
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    applied = 0
    for f in files:
        try:
            version = int(f.name.split("_", 1)[0])
        except ValueError:
            logger.warning("Ignoriere Migrations-Datei mit ungültigem Namen: %s", f.name)
            continue
        if version <= current:
            continue
        run_migration_script(
            conn, f.read_text(), f.name,
            lambda v=version: conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", (v, now_iso()),
            ),
        )
        applied += 1
        logger.info("Migration %s angewendet (Version %d)", f.name, version)
    if applied == 0:
        logger.debug("Keine neuen Migrations (aktuelle Version: %d)", current)
