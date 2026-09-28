"""Tests räumen nur auf, was sie selbst angelegt haben.

Hintergrund (26.09.2026): Die Suite lief aus Versehen gegen die echte
Datenbank. Aufräum-Fixtures mit `DELETE FROM <tabelle>` ohne WHERE haben dabei
das komplette Projekt-Audit-Log und alle Teamchat-Identitäten gelöscht, und
`_cleanup_external` hat ALLE externen Instanzen entfernt, auch echte.

Die Isolation in `_isolation.py` verhindert, dass es noch einmal passiert.
Dieses Modul ist die zweite Ebene: Selbst wenn die Isolation irgendwann bricht,
löscht ein Test nur Zeilen, die während des Tests neu dazugekommen sind.

Nutzung:

    with only_own_rows("project_audit_log"):
        yield            # Test läuft

Vor dem Test merkt sich der Helfer den höchsten rowid-Wert der Tabelle und
löscht danach nur Zeilen darüber. Zeilen, die es vorher schon gab, bleiben
unangetastet. Das gilt auch dann, wenn ein Test eine vorhandene Zeile ändert.
Liegt die Datenbank nicht im Test-Temp, verweigert der Helfer das Löschen ganz.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager

_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _max_rowid(conn, table: str) -> int:
    if not _TABLE.match(table):
        raise ValueError(f"ungültiger Tabellenname: {table!r}")
    row = conn.execute(f"SELECT COALESCE(MAX(rowid), 0) FROM {table}").fetchone()
    return int(row[0])


def delete_rows_after(conn, table: str, marker: int) -> int:
    """Löscht nur Zeilen mit rowid > marker. Gibt die Anzahl zurück."""
    if not _TABLE.match(table):
        raise ValueError(f"ungültiger Tabellenname: {table!r}")
    return conn.execute(f"DELETE FROM {table} WHERE rowid > ?", (marker,)).rowcount


def snapshot(*tables: str) -> dict[str, int]:
    """Merkt sich pro Tabelle den höchsten rowid-Wert."""
    from hydrahive.db.connection import db
    with db() as conn:
        return {t: _max_rowid(conn, t) for t in tables}


def refuse_real_db(db_path=None) -> None:
    """Dritte Ebene: Liegt die DB nicht im Test-Temp, wird gar nichts gelöscht."""
    from hydrahive.settings import settings
    from tests._isolation import forbidden_hit
    path = db_path if db_path is not None else settings.sessions_db
    bad = forbidden_hit(path)
    if bad is not None:
        raise RuntimeError(f"Aufräumen verweigert: {path} liegt im ECHTEN Verzeichnis {bad}.")


def cleanup(marks: dict[str, int]) -> None:
    """Löscht in jeder Tabelle nur die seit `snapshot()` neu dazugekommenen Zeilen."""
    from hydrahive.db.connection import db
    refuse_real_db()
    with db() as conn:
        for table, marker in marks.items():
            delete_rows_after(conn, table, marker)


@contextmanager
def only_own_rows(*tables: str) -> Iterator[None]:
    marks = snapshot(*tables)
    try:
        yield
    finally:
        cleanup(marks)
