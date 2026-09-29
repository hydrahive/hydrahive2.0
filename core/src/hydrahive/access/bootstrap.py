"""Anfangs-Freigaben und Übergang (docs/specs/access-groups.md §11, §12).

``apply_defaults()`` läuft bei jedem Start nach dem Laden der Module:
  - Neue Funktion mit default 'everyone' → everyone-Freigabe (Stufe use).
  - Neue Funktion mit default 'admin_only' → nichts, nur für Admins.
  - Bekannte Funktion → wird nie wieder angefasst (Admin-Änderungen bleiben).

``pending_notice()`` nennt die admin_only-Funktionen, die noch niemand
freigegeben und deren Hinweis der Admin noch nicht bestätigt hat.
"""
from __future__ import annotations

import logging

from hydrahive.access.capabilities import catalog
from hydrahive.access.store import audit
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)
_SYSTEM = "system"


def apply_defaults() -> list[str]:
    """Wendet Defaults auf neue Funktionen an. Gibt die neu gesehenen Funktionen zurück."""
    new: list[str] = []
    with db(immediate=True) as c:
        seen = {r[0] for r in c.execute("SELECT capability FROM access_seen_capabilities")}
        for cap in catalog().all():
            if cap.id in seen:
                continue
            c.execute(
                "INSERT INTO access_seen_capabilities (capability, default_kind, first_seen) VALUES (?, ?, ?)",
                (cap.id, cap.default, now_iso()),
            )
            if cap.default == "everyone":
                c.execute(
                    "INSERT OR IGNORE INTO access_capability_grants "
                    "(capability, subject_type, subject_id, level, granted_by, granted_at) "
                    "VALUES (?, 'everyone', '', 'use', ?, ?)",
                    (cap.id, _SYSTEM, now_iso()),
                )
            audit(c, _SYSTEM, "bootstrap_default", f"cap:{cap.id}", cap.default)
            new.append(cap.id)
    if new:
        logger.info("access: %d neue Funktionen nach Default eingerichtet: %s", len(new), ", ".join(new))
    return new


def pending_notice() -> list[str]:
    """admin_only-Funktionen ohne jede Freigabe, deren Hinweis noch offen ist."""
    declared = {c.id for c in catalog().all()}
    with db() as c:
        rows = c.execute(
            "SELECT s.capability FROM access_seen_capabilities s "
            "WHERE s.default_kind = 'admin_only' AND s.acknowledged = 0 "
            "AND NOT EXISTS (SELECT 1 FROM access_capability_grants g WHERE g.capability = s.capability) "
            "ORDER BY s.capability"
        ).fetchall()
    return [r[0] for r in rows if r[0] in declared]


def acknowledge_notice(*, actor_id: str) -> None:
    with db() as c:
        n = c.execute(
            "UPDATE access_seen_capabilities SET acknowledged = 1 "
            "WHERE default_kind = 'admin_only' AND acknowledged = 0"
        ).rowcount
        if n:
            audit(c, actor_id, "notice_acknowledged", "notice:admin_only", str(n))
