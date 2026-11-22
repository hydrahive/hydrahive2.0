"""Gemeinsame Taskpflege: fremde Einträge für die Module (docs/specs/federation-shared-tasks.md
§Kern-Schnittstelle). Aufgerufen über ``ModuleContext.catalog_foreign_list``.

``project_id`` steuert die Auswahl nach der Projektzuordnung (federation/catalog_project_map.py):
- lokale Projekt-ID: Einträge, die diesem Projekt zugeordnet sind (manuell oder gleicher Name);
- ``None``: nur Einträge ohne Projekt beim Ursprung (projektübergreifende Listen);
- ``"*"``: alle zugeordneten plus die ohne Projekt; ausgeblendete und nicht zugeordnete nie.

Ein ``ForeignItem`` hat die Metadaten wie im Katalog plus ``origin_fp``, ``origin_name``,
``foreign: True``, ``origin_last_seen``, ``stale``, ``pending_edits`` (bis G4 immer 0),
``project_id`` (Projekt beim Ursprung) und ``local_project_id`` (Zuordnung hier).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from hydrahive.db import federation_catalog_foreign as foreign_db
from hydrahive.federation.catalog_project_map import Resolver

logger = logging.getLogger(__name__)

ALL = "*"
MAX_LIMIT = 500
DEFAULT_INTERVAL = 300
FIELDS = ("origin_fp", "origin_name", "kind", "item_id", "owner", "title", "status", "priority",
          "project_id", "project_name", "created_at", "updated_at")


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _hub_stale(row: dict, now: datetime) -> bool:
    """Wie im Katalog-Reiter: länger als zwei Intervalle kein Push vom Ursprung."""
    last = _parse(row.get("last_push_at"))
    interval = row.get("interval_seconds") or DEFAULT_INTERVAL
    return last is None or (now - last).total_seconds() > 2 * interval


def hub_stale(mode: str, now: datetime | None = None) -> bool:
    """Client: Kopie gilt als nicht aktuell, wenn der Hub nicht erreichbar ist (gesperrt,
    entfernt, Sync aus) oder länger als zwei Intervalle kein Abholen gelang (Review #746)."""
    if mode == foreign_db.CLIENT_OFFLINE:
        return True
    last_pull, interval = foreign_db.pull_state()
    last = _parse(last_pull)
    now = now or datetime.now(timezone.utc)
    return last is None or (now - last).total_seconds() > 2 * interval


def _wanted(project_id: str | None, local: str | None, origin_project: str | None, hidden: bool) -> bool:
    if project_id is None:
        return not origin_project
    if project_id == ALL:
        return not origin_project or (local is not None and not hidden)
    return local == project_id


def is_admin_user(username: str) -> bool:
    """Rolle aus der Nutzerverwaltung (Module übergeben nur den Namen). Unbekannt → kein Admin."""
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(username)
    return bool(user and user.get("role") == "admin")


def foreign_list(kind: str, username: str, project_id: str | None = ALL, statuses: list[str] | None = None,
                 q: str | None = None, limit: int = 100, offset: int = 0, *,
                 is_admin: bool | None = None) -> list[dict]:
    """Fremde Einträge eines Nutzers. Wirft nie; ohne Gemeinsame Taskpflege leer."""
    try:
        if kind not in foreign_db.KINDS or not isinstance(username, str) or not username:
            return []
        mode = foreign_db.mode()
        if mode is None:
            return []
        statuses = [s for s in (statuses or []) if isinstance(s, str)][:12] or None
        q = q[:200] if isinstance(q, str) and q.strip() else None
        client = mode != foreign_db.HUB
        rows = (foreign_db.mirror_rows if client else foreign_db.hub_rows)(kind, username, statuses, q)
        resolver = Resolver(username, is_admin=is_admin_user(username) if is_admin is None else is_admin)
        now = datetime.now(timezone.utc)
        all_stale = client and hub_stale(mode, now)
        out: list[dict] = []
        for row in rows:
            a = resolver.resolve(row["origin_fp"], row.get("project_id"), row.get("project_name"))
            if not _wanted(project_id, a.local_project_id, row.get("project_id"), a.hidden):
                continue
            stale = (all_stale or bool(row.get("stale"))) if client else _hub_stale(row, now)
            out.append({**{f: row.get(f) for f in FIELDS}, "foreign": True,
                        "origin_last_seen": row.get("origin_last_seen"), "stale": stale,
                        "pending_edits": 0, "local_project_id": a.local_project_id})
        start = max(0, int(offset))
        return out[start:start + max(1, min(int(limit), MAX_LIMIT))]
    except Exception as e:  # nie in die Modul-Liste durchreichen
        logger.warning("catalog_foreign_list(%s, %s) fehlgeschlagen: %s", kind, username, e)
        return []
