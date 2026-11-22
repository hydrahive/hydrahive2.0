"""Gemeinsame Taskpflege: fremde Einträge eines Nutzers lesen (docs/specs/federation-shared-
tasks.md §Kern-Schnittstelle, ``ctx.catalog_foreign_list``).

Zwei Quellen, je nach Rolle der Instanz:
- **Client** (eigener Hub aktiv, ``shared``): die Kopie ``federation_catalog_mirror``, Stand der
  Ursprünge aus ``federation_catalog_mirror_instances``.
- **Hub** (nimmt von mindestens einem Partner an, ``shared``): der Katalog
  ``federation_catalog_items``, nur Partner, die Bedingung 2 erfüllen (catalog_accept,
  active, shared). Stand aus ``federation_catalog_sources``.

Immer nur ``owner`` = der angefragte Nutzer (AK G12, auch für Admins). Die Projektzuordnung
macht der Aufrufer (federation/catalog_foreign.py), hier wird nichts gespeichert.
"""
from __future__ import annotations

from hydrahive.db.connection import db

KINDS = ("task", "idea")
MAX_ROWS = 5000            # obere Grenze je Abfrage; die Zuordnung filtert danach in Python
_COLS = ("origin_fp", "origin_name", "kind", "item_id", "owner", "title", "status", "priority",
         "project_id", "project_name", "created_at", "updated_at")


def mode() -> str | None:
    """``client``, ``hub`` oder ``None`` (Gemeinsame Taskpflege aus bzw. ohne Hub/Partner)."""
    with db() as conn:
        row = conn.execute("SELECT enabled, shared FROM federation_catalog_settings WHERE id = 1").fetchone()
        if not row or not row["shared"]:
            return None
        hub = conn.execute("SELECT status FROM federation_peers WHERE is_hub = 1 LIMIT 1").fetchone()
        if hub and hub["status"] == "active" and row["enabled"]:
            return "client"
        if conn.execute("SELECT 1 FROM federation_peers WHERE catalog_accept = 1 LIMIT 1").fetchone():
            return "hub"
    return None


def _filters(statuses: list[str] | None, q: str | None, prefix: str) -> tuple[str, list]:
    parts, args = [], []
    if statuses:
        parts.append(f"{prefix}status IN ({','.join('?' * len(statuses))})")
        args += statuses
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        parts.append(f"({prefix}title LIKE ? ESCAPE '\\' OR {prefix}item_id LIKE ? ESCAPE '\\')")
        args += [f"%{escaped}%", f"{escaped}%"]
    return "".join(f" AND {p}" for p in parts), args


def mirror_rows(kind: str, username: str, statuses: list[str] | None, q: str | None) -> list[dict]:
    extra, args = _filters(statuses, q, "m.")
    sql = (
        f"SELECT {', '.join('m.' + c for c in _COLS)}, i.last_seen AS origin_last_seen, "
        "COALESCE(i.stale, 1) AS stale FROM federation_catalog_mirror m "
        "LEFT JOIN federation_catalog_mirror_instances i ON i.origin_fp = m.origin_fp "
        f"WHERE m.kind = ? AND m.owner = ?{extra} ORDER BY m.updated_at DESC, m.item_id LIMIT ?"
    )
    with db() as conn:
        rows = conn.execute(sql, (kind, username, *args, MAX_ROWS)).fetchall()
    return [dict(r) for r in rows]


def hub_rows(kind: str, username: str, statuses: list[str] | None, q: str | None) -> list[dict]:
    extra, args = _filters(statuses, q, "i.")
    sql = (
        "SELECT p.fingerprint AS origin_fp, p.name AS origin_name, i.kind, i.item_id, i.owner, i.title, "
        "i.status, i.priority, i.project_id, i.project_name, i.created_at, i.updated_at, "
        "p.last_seen AS origin_last_seen, s.last_push_at, s.interval_seconds "
        "FROM federation_catalog_items i JOIN federation_peers p ON p.id = i.peer_id "
        "LEFT JOIN federation_catalog_sources s ON s.peer_id = i.peer_id "
        "WHERE i.kind = ? AND i.owner = ? AND p.catalog_accept = 1 AND p.status = 'active' "
        f"AND COALESCE(s.shared, 0) = 1{extra} ORDER BY i.updated_at DESC, i.item_id LIMIT ?"
    )
    with db() as conn:
        rows = conn.execute(sql, (kind, username, *args, MAX_ROWS)).fetchall()
    return [dict(r) for r in rows]


def mirror_row(kind: str, username: str, origin_fp: str, item_id: str) -> dict | None:
    """Ein Eintrag der Kopie (für ``catalog_foreign_get``, wenn der Hub nicht antwortet)."""
    with db() as conn:
        row = conn.execute(
            f"SELECT {', '.join('m.' + c for c in _COLS)}, i.last_seen AS origin_last_seen, "
            "COALESCE(i.stale, 1) AS stale FROM federation_catalog_mirror m "
            "LEFT JOIN federation_catalog_mirror_instances i ON i.origin_fp = m.origin_fp "
            "WHERE m.kind = ? AND m.owner = ? AND m.origin_fp = ? AND m.item_id = ?",
            (kind, username, origin_fp, item_id),
        ).fetchone()
    return dict(row) if row else None
