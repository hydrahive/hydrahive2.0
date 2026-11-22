"""Gemeinsame Taskpflege: manuelle Projektzuordnung speichern und die Ursprungsprojekte
auflisten, von denen ein Nutzer Einträge sieht (docs/specs/federation-shared-tasks.md
§Projektzuordnung, §Korrektur im Cockpit).

Ursprungsprojekte kommen auf einem Client aus der Kopie (``federation_catalog_mirror``)
und auf dem Hub aus dem Katalog (``federation_catalog_items`` mit dem Fingerprint des
Partners). Eine Instanz, die beides hat, liefert beides. Sichtbar sind nur Einträge
mit ``owner`` = eigener Nutzername (wie in den Modul-Listen, auch für Admins).
"""
from __future__ import annotations

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

HIDDEN = "hidden"

_MIRROR = (
    "SELECT origin_fp, MAX(origin_name) AS origin_name, project_id, MAX(project_name) AS project_name, "
    "COUNT(*) AS n FROM federation_catalog_mirror WHERE owner = ? AND project_id IS NOT NULL "
    "GROUP BY origin_fp, project_id"
)
_HUB = (
    "SELECT p.fingerprint AS origin_fp, MAX(p.name) AS origin_name, i.project_id, "
    "MAX(i.project_name) AS project_name, COUNT(*) AS n FROM federation_catalog_items i "
    "JOIN federation_peers p ON p.id = i.peer_id "
    "LEFT JOIN federation_catalog_sources s ON s.peer_id = i.peer_id "
    "WHERE i.owner = ? AND i.project_id IS NOT NULL "
    "AND p.catalog_accept = 1 AND p.status = 'active' AND COALESCE(s.shared, 0) = 1 "   # wie hub_rows
    "GROUP BY p.fingerprint, i.project_id"
)


def origin_projects(username: str) -> list[dict]:
    """Ursprungsprojekte mit Anzahl sichtbarer Einträge, zusammengeführt je (origin_fp, project_id)."""
    merged: dict[tuple[str, str], dict] = {}
    with db() as conn:
        rows = conn.execute(_MIRROR, (username,)).fetchall() + conn.execute(_HUB, (username,)).fetchall()
    for r in rows:
        key = (r["origin_fp"], r["project_id"])
        entry = merged.setdefault(key, {"origin_fp": r["origin_fp"], "origin_name": r["origin_name"],
                                        "origin_project_id": r["project_id"],
                                        "project_name": r["project_name"], "count": 0})
        entry["count"] += int(r["n"])
        entry["origin_name"] = entry["origin_name"] or r["origin_name"]
        entry["project_name"] = entry["project_name"] or r["project_name"]
    return sorted(merged.values(), key=lambda e: (e["origin_name"] or "", e["project_name"] or "",
                                                  e["origin_project_id"]))


def set_target(username: str, origin_fp: str, origin_project_id: str, target: str | None) -> None:
    """``target`` = lokale project_id oder ``hidden``; ``None`` = zurück auf „automatisch“ (Zeile weg)."""
    with db() as conn:
        if target is None:
            conn.execute(
                "DELETE FROM federation_catalog_project_map WHERE username = ? AND origin_fp = ? "
                "AND origin_project_id = ?", (username, origin_fp, origin_project_id),
            )
            return
        conn.execute(
            "INSERT INTO federation_catalog_project_map (username, origin_fp, origin_project_id, target, updated_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (username, origin_fp, origin_project_id) "
            "DO UPDATE SET target = excluded.target, updated_at = excluded.updated_at",
            (username, origin_fp, origin_project_id, target, now_iso()),
        )


def manual_rows(username: str) -> dict[tuple[str, str], str]:
    with db() as conn:
        rows = conn.execute(
            "SELECT origin_fp, origin_project_id, target FROM federation_catalog_project_map WHERE username = ?",
            (username,),
        ).fetchall()
    return {(r["origin_fp"], r["origin_project_id"]): r["target"] for r in rows}
