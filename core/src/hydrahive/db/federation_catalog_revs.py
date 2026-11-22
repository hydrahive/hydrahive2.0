"""Hub: Änderungsnummer `rev` + Löschprotokoll (docs/specs/federation-shared-
tasks.md §Änderungsnummer, §Schalter).

``next_rev`` vergibt die nächste `rev` aus dem gemeinsamen Zähler
``federation_catalog_counter`` — ein Zähler für Upserts in
``federation_catalog_items`` UND für Löschzeilen in
``federation_catalog_deletions`` (Spec: "fortlaufende Änderungsnummer ...
global auf dem Hub"). Muss innerhalb derselben Transaktion aufgerufen werden,
die die Zeile schreibt, sonst entstehen Lücken oder doppelte Werte bei
gleichzeitigen Schreibern (Schreibsperre kommt von ``db(immediate=True)`` im
Aufrufer).

``write_deletion`` legt eine Zeile ins Löschprotokoll, inklusive eigener
`rev`. ``purge_deletions``/``min_partial_rev`` siehe §Aufräumen (Auftrag B,
Stück 3).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

RETENTION_DAYS = 7


def next_rev(conn: sqlite3.Connection) -> int:
    """Nächste `rev`, streng steigend, gemeinsam für Items und Löschzeilen.

    Muss in derselben Transaktion laufen wie das Upsert/die Löschzeile, die
    diese `rev` verwendet (Aufrufer hält die Schreibsperre).
    """
    conn.execute("UPDATE federation_catalog_counter SET rev = rev + 1 WHERE id = 1")
    row = conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()
    return int(row["rev"])


def write_deletion(
    conn: sqlite3.Connection,
    *,
    origin_fp: str,
    kind: str,
    item_id: str,
    owner: str,
    deleted_at: str,
) -> int:
    """Eine Zeile ins Löschprotokoll, mit eigener `rev`. Gibt die vergebene
    `rev` zurück."""
    rev = next_rev(conn)
    conn.execute(
        "INSERT INTO federation_catalog_deletions "
        "(rev, origin_fp, kind, item_id, owner, deleted_at) VALUES (?, ?, ?, ?, ?, ?)",
        (rev, origin_fp, kind, item_id, owner, deleted_at),
    )
    return rev


def purge_deletions(now: datetime | None = None) -> int:
    """Entfernt Löschzeilen älter als ``RETENTION_DAYS`` Tage; merkt sich den
    höchsten entfernten `rev`-Wert in ``federation_catalog_counter.purged_rev``
    (damit V2 erkennt, wann ein Client zu alt für Teilabgleich ist).

    Eigene Verbindung/Transaktion (Aufrufer aus dem Katalog-Timer-Loop, kein
    laufender Push/Pull offen). Gibt die Anzahl der entfernten Zeilen zurück.
    """
    from hydrahive.db.connection import db

    cutoff = ((now or datetime.now(timezone.utc)) - timedelta(days=RETENTION_DAYS)).isoformat(
        timespec="milliseconds",
    )
    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT MAX(rev) AS maxrev FROM federation_catalog_deletions WHERE deleted_at < ?",
            (cutoff,),
        ).fetchone()
        maxrev = row["maxrev"] if row else None
        cur = conn.execute(
            "DELETE FROM federation_catalog_deletions WHERE deleted_at < ?", (cutoff,),
        )
        if maxrev is not None:
            conn.execute(
                "UPDATE federation_catalog_counter SET purged_rev = MAX(purged_rev, ?) WHERE id = 1",
                (int(maxrev),),
            )
        return cur.rowcount


def min_partial_rev() -> int:
    """Kleinste `rev`, ab der ein Teilabgleich noch vollständig ist
    (= höchste bisher aufgeräumte `rev`). Ein Client mit `after_rev` darunter
    braucht einen vollen Abgleich, weil dazwischen Löschzeilen fehlen könnten.
    """
    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute("SELECT purged_rev FROM federation_catalog_counter WHERE id = 1").fetchone()
    return int(row["purged_rev"]) if row else 0
