"""Client: Kopie der Hub-Metadaten lesen (docs/specs/federation-shared-tasks.md
§Oberfläche Cockpit, Katalog-Reiter auf Clients, nur lesen).

Gleiche Sichtbarkeit wie ``GET /api/federation/catalog``: ein Nutzer sieht nur
Einträge mit seinem Nutzernamen als ``owner``, Admins sehen alles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hydrahive.db.connection import db

MAX_LIMIT = 200
MAX_OFFSET = 10_000
_COLS = ("origin_fp", "origin_name", "kind", "item_id", "owner", "title", "status", "priority",
         "project_id", "project_name", "created_at", "updated_at", "received_at")


@dataclass
class MirrorFilter:
    owners: list[str] | None = None          # None = alle (Admin)
    instances: list[str] | None = None       # origin_fp
    project: str | None = None               # project_name (wie in der Hub-Ansicht)
    statuses: list[str] = field(default_factory=list)
    kind: str | None = None
    q: str | None = None
    limit: int = 50
    offset: int = 0


def _where(f: MirrorFilter) -> tuple[str, list]:
    parts, args = [], []
    if f.owners is not None:
        if not f.owners:
            return "WHERE 0", []
        parts.append(f"owner IN ({','.join('?' * len(f.owners))})")
        args += f.owners
    if f.instances:
        parts.append(f"origin_fp IN ({','.join('?' * len(f.instances))})")
        args += f.instances
    if f.project:
        parts.append("project_name = ?")
        args.append(f.project)
    if f.statuses:
        parts.append(f"status IN ({','.join('?' * len(f.statuses))})")
        args += f.statuses
    if f.kind:
        parts.append("kind = ?")
        args.append(f.kind)
    if f.q:
        escaped = f.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        parts.append("(title LIKE ? ESCAPE '\\' OR item_id LIKE ? ESCAPE '\\')")
        args += [f"%{escaped}%", f"{escaped}%"]
    return ("WHERE " + " AND ".join(parts)) if parts else "", args


def list_page(f: MirrorFilter) -> dict:
    """Eine Seite, neueste Änderung zuerst. ``has_more`` statt teurer Zählung."""
    limit = max(1, min(int(f.limit), MAX_LIMIT))
    offset = max(0, min(int(f.offset), MAX_OFFSET))
    where, args = _where(f)
    with db() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(_COLS)} FROM federation_catalog_mirror {where} "
            "ORDER BY updated_at DESC, origin_fp, kind, item_id LIMIT ? OFFSET ?",
            (*args, limit + 1, offset),
        ).fetchall()
    items = [{**dict(r), "short_id": str(r["item_id"])[:8]} for r in rows[:limit]]
    return {"items": items, "has_more": len(rows) > limit, "limit": limit, "offset": offset}


def facets(owners: list[str] | None) -> dict:
    """Werte für die Filter: Instanzen (fp + Name) und Projektnamen, nur aus Sichtbarem."""
    where, args = _where(MirrorFilter(owners=owners))
    with db() as conn:
        inst = conn.execute(
            f"SELECT origin_fp, MAX(origin_name) AS origin_name, COUNT(*) AS n FROM federation_catalog_mirror "
            f"{where} GROUP BY origin_fp ORDER BY origin_name", args,
        ).fetchall()
        sep = " AND " if where else "WHERE "
        projects = conn.execute(
            f"SELECT DISTINCT project_name FROM federation_catalog_mirror {where}{sep}project_name IS NOT NULL "
            "ORDER BY project_name", args,
        ).fetchall()
    return {
        "instances": [{"origin_fp": r["origin_fp"], "origin_name": r["origin_name"], "count": r["n"]} for r in inst],
        "projects": [r["project_name"] for r in projects],
    }


def count() -> int:
    with db() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM federation_catalog_mirror").fetchone()[0])
