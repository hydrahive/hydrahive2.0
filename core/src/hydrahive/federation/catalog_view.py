"""Hub: Katalog-Liste (docs/specs/federation-catalog.md §API, §Oberfläche).

``list_catalog(owners, params)`` mischt die Katalogzeilen der Partner mit den
EIGENEN Einträgen des Hubs (direkt aus den Modul-Quellen über ``query(...)``,
nicht kopiert), sortiert nach ``updated_at`` absteigend und schneidet die Seite
aus. Die Funktion kennt keine Anmeldung: wer was sehen darf, entscheidet der
Aufrufer über ``owners`` (None = alle). Heute ruft sie nur die Cockpit-Route;
eine spätere signierte Abfrage eines Clients kann sie genauso nutzen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from hydrahive.db import federation_catalog_view as view_db
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)

LOCAL = "local"           # Instanz-ID für die eigenen Einträge des Hubs
KINDS = ("task", "idea")
OPEN_STATUSES = {"task": ("open", "in_progress"), "idea": ("new", "review", "planned")}
DEFAULT_INTERVAL = 300
MAX_OFFSET = 4_700        # offset + limit + 1 bleibt unter der query-Grenze der Modul-Quellen (5000)


@dataclass
class ListParams:
    instances: list[str] | None = None     # Partner-IDs und/oder "local"; None = alle
    project: str | None = None
    statuses: list[str] = field(default_factory=list)
    open_only: bool = False
    kind: str | None = None
    q: str | None = None
    limit: int = 50
    offset: int = 0


def _sort_key(item: dict) -> tuple[str, str]:
    """updated_at absteigend; Formate der Quellen (Sekunden vs. Mikrosekunden) auf
    die Sekunde angeglichen, damit Ideen und Tasks sinnvoll gemischt werden."""
    stamp = str(item.get("updated_at") or "")
    return stamp[:19], stamp


def _statuses(params: ListParams, kind: str) -> list[str]:
    wanted = list(params.statuses)
    if params.open_only:
        wanted = [s for s in OPEN_STATUSES[kind] if not wanted or s in wanted]
    return wanted


def _local_project_id(project: str | None) -> str | None:
    """Filter kann Projektname oder -ID sein; die Quellen kennen nur die ID."""
    if not project:
        return None
    try:
        from hydrahive.projects import _config_io as projects
        for p in projects.list_all():
            if project in (p.get("id"), p.get("name")):
                return p.get("id")
    except Exception as e:
        logger.debug("Katalog: Projektliste nicht lesbar: %s", e)
    return project


def _local_items(owners: list[str] | None, params: ListParams, want: int) -> list[dict]:
    if params.instances is not None and LOCAL not in params.instances:
        return []
    if owners is None:
        from hydrahive.api.middleware.users import list_users
        owners = [u["username"] for u in list_users()]
    if not owners:
        return []
    project = _local_project_id(params.project)
    out: list[dict] = []
    for kind in KINDS:
        if params.kind and params.kind != kind:
            continue
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        statuses = _statuses(params, kind)
        if (params.statuses or params.open_only) and not statuses:
            continue
        for status in statuses or [None]:
            try:
                rows = source.query(owners, project, status, params.q or None, want, 0) or []
            except Exception as e:
                logger.warning("Katalog: eigene Quelle %s nicht lesbar: %s", kind, e)
                break
            for r in rows:
                if isinstance(r, dict) and r.get("owner") in owners:
                    out.append({**r, "kind": kind, "peer_id": None, "instance": None, "local": True})
    return out


def _remote_items(owners: list[str] | None, params: ListParams, want: int) -> list[dict]:
    peer_ids = None if params.instances is None else [i for i in params.instances if i != LOCAL]
    statuses = list(params.statuses)
    if params.open_only:
        allowed = {s for kind in KINDS if not params.kind or params.kind == kind for s in OPEN_STATUSES[kind]}
        statuses = [s for s in (statuses or sorted(allowed)) if s in allowed]
        if not statuses:
            return []
    rows = view_db.list_rows(view_db.RowFilter(
        owners=owners, peer_ids=peer_ids, project=params.project, statuses=statuses,
        kind=params.kind, q=params.q,
    ), want)
    return [{**r, "instance": r.pop("peer_name"), "local": False,
             "snapshot_stale": bool(r.get("snapshot_stale"))} for r in rows]


def _public(item: dict) -> dict:
    keys = ("peer_id", "instance", "local", "kind", "item_id", "owner", "title", "status", "priority",
            "project_id", "project_name", "created_at", "updated_at", "snapshot_at", "snapshot_stale")
    out = {k: item.get(k) for k in keys}
    out["short_id"] = str(item.get("item_id") or "")[:8]
    out["snapshot_stale"] = bool(out["snapshot_stale"])
    return out


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def instance_list(*, with_counts: bool, now: datetime | None = None) -> list[dict]:
    """Partner + „dieser Server“; ``stale`` = länger als zwei Intervalle nichts gehört."""
    now = now or datetime.now(timezone.utc)
    out = [{"id": LOCAL, "name": None, "local": True, "stale": False, "last_seen": None, "last_push_at": None}]
    for r in view_db.instances():
        last = _parse(r["last_push_at"])
        interval = r["interval_seconds"] or DEFAULT_INTERVAL
        entry = {
            "id": r["id"], "name": r["name"], "local": False, "status": r["status"],
            "last_seen": r["last_seen"], "last_push_at": r["last_push_at"],
            "interval_seconds": interval,
            "stale": last is None or (now - last).total_seconds() > 2 * interval,
        }
        if with_counts:
            entry["item_count"] = r["item_count"]
        else:  # Nicht-Admins: nur, was die Anzeige braucht
            entry = {k: entry[k] for k in ("id", "name", "local", "stale")}
        out.append(entry)
    return out


def list_catalog(owners: list[str] | None, params: ListParams) -> dict:
    """Eine Seite des Katalogs. ``owners``: sichtbare Nutzernamen, None = alle (Admin)."""
    limit = max(1, min(int(params.limit), 200))
    offset = max(0, min(int(params.offset), MAX_OFFSET))
    want = offset + limit + 1
    merged = _remote_items(owners, params, want) + _local_items(owners, params, want)
    merged.sort(key=_sort_key, reverse=True)
    page = merged[offset:offset + limit]
    return {
        "items": [_public(i) for i in page],
        "offset": offset,
        "limit": limit,
        "has_more": len(merged) > offset + limit,
        "instances": instance_list(with_counts=owners is None),
    }
