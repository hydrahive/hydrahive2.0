"""Hub: Datenbankseite von ``catalog_pull`` (docs/specs/federation-shared-tasks.md
§Nachricht catalog_pull, §Schalter Bedingungen 1–5).

Nur Partner-Einträge aus ``federation_catalog_items`` und das Löschprotokoll.
Eigene Einträge des Hubs liest ``federation/catalog_pull_own.py`` über die
Katalog-Quellen (sie stehen nie in ``federation_catalog_items``).

Sichtbar für Client C ist ein Partner-Eintrag von Ursprung O genau dann, wenn
O ``catalog_accept = 1``, ``status = active`` und ``shared = 1`` meldet
(Bedingung 2, gleiche Regel wie ``catalog_visibility.origin_visible``), O ≠ C
(Bedingung 5) und ``owner`` in der Nutzerliste von C steht (Bedingung 4).
Bedingungen 1 und 3 prüft ``federation/catalog_pull.py`` vorher.
"""
from __future__ import annotations

import json

from hydrahive.db.connection import db

# Bedingung 2 als SQL, gleichbedeutend mit catalog_visibility.origin_visible
_VISIBLE_ORIGIN = (
    "p.catalog_accept = 1 AND p.status = 'active' AND COALESCE(s.shared, 0) = 1 AND p.id <> ?"
)
_ITEM_COLS = (
    "i.kind, i.item_id, i.owner, i.title, i.status, i.priority, i.project_id, i.project_name, "
    "i.created_at, i.updated_at, i.rev, p.fingerprint AS origin_fp, p.name AS origin_name"
)


def _in(values: list[str]) -> str:
    return ",".join("?" * len(values))


def items_after(client_id: str, users: list[str], after_rev: int, upto: int, limit: int) -> list[dict]:
    """Partner-Einträge mit ``after_rev < rev <= upto``, sichtbar für C, nach rev sortiert."""
    if not users:
        return []
    sql = (
        f"SELECT {_ITEM_COLS} FROM federation_catalog_items i "
        "JOIN federation_peers p ON p.id = i.peer_id "
        "LEFT JOIN federation_catalog_sources s ON s.peer_id = i.peer_id "
        f"WHERE i.rev > ? AND i.rev <= ? AND {_VISIBLE_ORIGIN} AND i.owner IN ({_in(users)}) "
        "ORDER BY i.rev LIMIT ?"
    )
    with db() as conn:
        rows = conn.execute(sql, (int(after_rev), int(upto), client_id, *users, int(limit))).fetchall()
    return [dict(r) for r in rows]


def deletions_after(client_fp: str, users: list[str], after_rev: int, upto: int, limit: int) -> list[dict]:
    """Löschzeilen mit ``after_rev < rev <= upto`` für Nutzer von C, nie über C selbst.

    Die Sichtbarkeit von O wird hier bewusst NICHT geprüft: Fällt sie weg,
    sind genau diese Zeilen das Signal an C, die Einträge zu entfernen.
    """
    if not users:
        return []
    sql = (
        "SELECT rev, origin_fp, kind, item_id FROM federation_catalog_deletions "
        f"WHERE rev > ? AND rev <= ? AND origin_fp <> ? AND owner IN ({_in(users)}) ORDER BY rev LIMIT ?"
    )
    with db() as conn:
        rows = conn.execute(sql, (int(after_rev), int(upto), client_fp, *users, int(limit))).fetchall()
    return [dict(r) for r in rows]


def current_rev() -> int:
    """Obergrenze für eine Seite. Zuerst lesen: rev und Zeile werden in derselben
    Transaktion geschrieben, alles bis hierhin ist also schon sichtbar."""
    with db() as conn:
        row = conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()
    return int(row["rev"]) if row else 0


def visible_keys(client_id: str, users: list[str]) -> list[list[str]]:
    """Alle für C sichtbaren Partner-Schlüssel ``[origin_fp, kind, item_id, updated_at]``,
    stabil sortiert (für ``full_keys``)."""
    if not users:
        return []
    sql = (
        "SELECT p.fingerprint AS origin_fp, i.kind, i.item_id, i.updated_at "
        "FROM federation_catalog_items i JOIN federation_peers p ON p.id = i.peer_id "
        "LEFT JOIN federation_catalog_sources s ON s.peer_id = i.peer_id "
        f"WHERE {_VISIBLE_ORIGIN} AND i.owner IN ({_in(users)}) "
        "ORDER BY p.fingerprint, i.kind, i.item_id"
    )
    with db() as conn:
        rows = conn.execute(sql, (client_id, *users)).fetchall()
    return [[r["origin_fp"], r["kind"], r["item_id"], r["updated_at"] or ""] for r in rows]


def instances(client_id: str) -> list[dict]:
    """Sichtbare Ursprünge außer C mit Stand (für ``instances``)."""
    sql = (
        "SELECT p.fingerprint AS origin_fp, p.name AS origin_name, p.last_seen, "
        "s.last_push_at, s.interval_seconds FROM federation_peers p "
        "LEFT JOIN federation_catalog_sources s ON s.peer_id = p.id "
        f"WHERE {_VISIBLE_ORIGIN} ORDER BY p.name"
    )
    with db() as conn:
        rows = conn.execute(sql, (client_id,)).fetchall()
    return [dict(r) for r in rows]


def record_pull(client_id: str, seq: int, users: list[str], now: str, *, local_empty: bool) -> bool:
    """``seq`` verbuchen (derselbe Zähler wie beim Push), ``pull_users`` und
    ``last_pull_at`` merken, ``reset_local`` auswerten — alles in EINER
    Transaktion. Rückgabe: ``reset_local`` an C melden.

    ``reset_local`` bleibt gesetzt, bis C mit leerem ``local_after`` abholt
    (``local_empty``), also seinen Cursor für Hub-Einträge wirklich auf „von
    vorn“ gestellt hat. Geht eine Antwort verloren, kommt die Meldung beim
    nächsten Abholen also noch einmal.

    Wirft ``SeqReplay`` aus federation_catalog_hub, wenn ``seq`` inzwischen
    nicht mehr neuer ist (gleichzeitige Nachricht mit derselben seq).
    """
    from hydrahive.db.federation_catalog_hub import SeqReplay

    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT last_seq, reset_local FROM federation_catalog_sources WHERE peer_id = ?", (client_id,),
        ).fetchone()
        current = int(row["last_seq"]) if row else 0
        if seq <= current:
            raise SeqReplay(current)
        pending = bool(row and row["reset_local"]) and not local_empty
        conn.execute(
            "INSERT INTO federation_catalog_sources (peer_id, last_seq, pull_users, last_pull_at, reset_local) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (peer_id) DO UPDATE SET last_seq = excluded.last_seq, "
            "pull_users = excluded.pull_users, last_pull_at = excluded.last_pull_at, "
            "reset_local = excluded.reset_local",
            (client_id, int(seq), json.dumps(sorted(set(users))), now, 1 if pending else 0),
        )
    return pending


def client_shared(client_id: str) -> bool:
    """Bedingung 3, Teil „C meldet shared“ (zuletzt im Push gemeldet)."""
    with db() as conn:
        row = conn.execute(
            "SELECT shared FROM federation_catalog_sources WHERE peer_id = ?", (client_id,),
        ).fetchone()
    return bool(row and row["shared"])
