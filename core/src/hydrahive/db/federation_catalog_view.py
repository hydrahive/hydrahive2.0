"""Hub: Katalog lesen und Snapshots schreiben (docs/specs/federation-catalog.md §API, §Ablauf 4).

Nur ``federation_catalog_items`` (+ FTS, Partner, Quellen-Status). Die eigenen
Einträge des Hubs kommen nicht von hier, sondern aus den Modul-Quellen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hydrahive.db.connection import db

ITEM_COLUMNS = (
    "i.peer_id, i.kind, i.item_id, i.owner, i.title, i.status, i.priority, i.project_id, i.project_name, "
    "i.created_at, i.updated_at, i.received_at, i.snapshot_at, i.snapshot_stale, p.name AS peer_name"
)


@dataclass
class RowFilter:
    owners: list[str] | None = None          # None = alle (Admin)
    peer_ids: list[str] | None = None        # None = alle Partner
    project: str | None = None               # project_name ODER project_id
    statuses: list[str] = field(default_factory=list)
    kind: str | None = None
    q: str | None = None


def fts_query(q: str | None) -> str | None:
    """Suchtext → FTS5-Ausdruck: jedes Wort als Präfix, Anführungszeichen maskiert."""
    words = [w for w in (q or "").split() if w]
    if not words:
        return None
    return " ".join('"' + w.replace('"', '""') + '"*' for w in words[:10])


def _where(f: RowFilter) -> tuple[str, list]:
    clauses, args = ["1 = 1"], []
    if f.owners is not None:
        if not f.owners:
            return "0 = 1", []
        clauses.append(f"i.owner IN ({', '.join('?' * len(f.owners))})")
        args += f.owners
    if f.peer_ids is not None:
        if not f.peer_ids:
            return "0 = 1", []
        clauses.append(f"i.peer_id IN ({', '.join('?' * len(f.peer_ids))})")
        args += f.peer_ids
    if f.project:
        clauses.append("(i.project_name = ? OR i.project_id = ?)")
        args += [f.project, f.project]
    if f.statuses:
        clauses.append(f"i.status IN ({', '.join('?' * len(f.statuses))})")
        args += f.statuses
    if f.kind:
        clauses.append("i.kind = ?")
        args.append(f.kind)
    match = fts_query(f.q)
    if match:
        clauses.append("i.rowid IN (SELECT rowid FROM federation_catalog_fts WHERE federation_catalog_fts MATCH ?)")
        args.append(match)
    return " AND ".join(clauses), args


def list_rows(f: RowFilter, limit: int) -> list[dict]:
    """Neueste Änderung zuerst (innerhalb der Tabelle; gemischt wird in catalog_view)."""
    where, args = _where(f)
    with db() as conn:
        rows = conn.execute(
            f"SELECT {ITEM_COLUMNS} FROM federation_catalog_items i "
            f"JOIN federation_peers p ON p.id = i.peer_id WHERE {where} "
            "ORDER BY i.updated_at DESC, i.item_id DESC LIMIT ?",
            [*args, limit],
        ).fetchall()
    return [dict(r) for r in rows]


def get_row(peer_id: str, kind: str, item_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            f"SELECT {ITEM_COLUMNS}, i.snapshot_body FROM federation_catalog_items i "
            "JOIN federation_peers p ON p.id = i.peer_id "
            "WHERE i.peer_id = ? AND i.kind = ? AND i.item_id = ?",
            (peer_id, kind, item_id),
        ).fetchone()
    return dict(row) if row else None


_META = ("title", "status", "priority", "project_id", "project_name", "created_at", "updated_at")


def save_fetch(peer_id: str, kind: str, item_id: str, meta: dict, text: str, now: str) -> dict | None:
    """Live nachgeladen: Metadaten nachziehen (nur bei ``updated_at`` ≥ gespeichert)
    und den Text als Snapshot speichern. Der Snapshot wird immer ganz ersetzt."""
    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT updated_at FROM federation_catalog_items WHERE peer_id = ? AND kind = ? AND item_id = ?",
            (peer_id, kind, item_id),
        ).fetchone()
        if row is None:
            return None
        fields: dict[str, object] = {"snapshot_body": text, "snapshot_at": now, "snapshot_stale": 0}
        if isinstance(meta.get("updated_at"), str) and meta["updated_at"] >= (row["updated_at"] or ""):
            fields.update({k: meta.get(k) for k in _META if k in meta})
        conn.execute(
            f"UPDATE federation_catalog_items SET {', '.join(f'{k} = ?' for k in fields)} "
            "WHERE peer_id = ? AND kind = ? AND item_id = ?",
            [*fields.values(), peer_id, kind, item_id],
        )
    return get_row(peer_id, kind, item_id)


def drop_snapshot(peer_id: str, kind: str, item_id: str) -> None:
    """Ursprung gibt den Eintrag nicht mehr heraus (gelöscht, ausgeschlossen): Snapshot weg."""
    with db() as conn:
        conn.execute(
            "UPDATE federation_catalog_items SET snapshot_body = NULL, snapshot_at = NULL, snapshot_stale = 0 "
            "WHERE peer_id = ? AND kind = ? AND item_id = ?",
            (peer_id, kind, item_id),
        )


def instances() -> list[dict]:
    """Partner, die Katalog-Daten schicken (dürfen) — mit Status für „nicht aktuell“."""
    with db() as conn:
        rows = conn.execute(
            "SELECT p.id, p.name, p.status, p.last_seen, p.catalog_accept, "
            "s.last_push_at, s.last_full_at, s.interval_seconds, COALESCE(s.item_count, 0) AS item_count "
            "FROM federation_peers p LEFT JOIN federation_catalog_sources s ON s.peer_id = p.id "
            "WHERE p.catalog_accept = 1 OR s.peer_id IS NOT NULL ORDER BY p.name",
        ).fetchall()
    return [dict(r) for r in rows]
