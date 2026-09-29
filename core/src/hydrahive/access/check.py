"""Entscheidung „darf dieser Nutzer diese Funktion?“ (docs/specs/access-groups.md §7).

Regeln:
  1. Admins dürfen alles (Stufe manage).
  2. Nicht deklarierte Funktionen sind für alle offen.
  3. Sonst zählt die höchste Stufe aus: everyone, direkte Freigabe, Gruppen.
  4. Kann nicht entschieden werden (Fehler), wird abgelehnt (fail-closed).

Geprüft wird immer mit der stabilen user_id. Wer nur den Namen hat
(Sessions und ToolContext speichern heute den Namen), löst über
``user_id_for()`` auf.
"""
from __future__ import annotations

import logging

from hydrahive.access import grants, store
from hydrahive.access.capabilities import catalog
from hydrahive.access.grants import LEVEL_RANK

logger = logging.getLogger(__name__)


def user_id_for(username: str) -> str | None:
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(username)
    return user["user_id"] if user else None


def _levels(user_id: str) -> dict[str, str]:
    rows = grants.grants_matching(user_id=user_id, group_ids=store.groups_of(user_id))
    best: dict[str, str] = {}
    for r in rows:
        cur = best.get(r["capability"])
        if cur is None or LEVEL_RANK[r["level"]] > LEVEL_RANK[cur]:
            best[r["capability"]] = r["level"]
    return best


def level(*, user_id: str, role: str, capability: str) -> str | None:
    """Stufe des Nutzers für diese Funktion: 'manage', 'use' oder None (kein Zugriff)."""
    if role == "admin":
        return "manage"
    if not catalog().is_declared(capability):
        return "use"
    try:
        return _levels(user_id).get(capability)
    except Exception:  # noqa: BLE001 — jede Störung führt zu Ablehnung, nie zu Zugriff
        logger.exception("access: Prüfung %s für %s fehlgeschlagen (fail-closed)", capability, user_id)
        return None


def can_use(*, user_id: str, role: str, capability: str) -> bool:
    return level(user_id=user_id, role=role, capability=capability) is not None


def can_manage(*, user_id: str, role: str, capability: str) -> bool:
    return level(user_id=user_id, role=role, capability=capability) == "manage"


def capabilities_for(*, user_id: str, role: str) -> dict[str, str]:
    """Alle deklarierten Funktionen, die der Nutzer hat, mit Stufe (für /api/access/me)."""
    declared = [c.id for c in catalog().all()]
    if role == "admin":
        return {cap: "manage" for cap in declared}
    try:
        levels = _levels(user_id)
    except Exception:  # noqa: BLE001
        logger.exception("access: capabilities_for %s fehlgeschlagen (fail-closed)", user_id)
        return {}
    return {cap: levels[cap] for cap in declared if cap in levels}


def can_use_as(username: str, capability: str) -> bool:
    """Prüfung für Werkzeuge und Läufe, die nur den Nutzernamen kennen (ToolContext.user_id).

    Löst Namen → stabile user_id + aktuelle Rolle auf. Unbekannter Nutzer → False.
    """
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(username)
    if user is None:
        return False
    return can_use(user_id=user["user_id"], role=user["role"], capability=capability)
