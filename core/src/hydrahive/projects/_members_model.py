"""Einzige maßgebliche Abstraktion über die Projekt-Member-Struktur.

Das Feld ``project["members"]`` ist eine ``list[{username, role}]``.
NIEMAND außerhalb dieses Moduls greift direkt auf die Struktur zu — alle
Membership-/Rollen-Fragen laufen über ``role_of`` / ``usernames`` /
``has_at_least``. So bleibt das Speicherformat an genau einer Stelle gekapselt.

``created_by`` ist implizit ``admin`` (auch wenn er nicht in ``members`` steht).
"""
from __future__ import annotations

from typing import Any

ROLES = ("read", "write", "admin")
DEFAULT_ROLE = "write"
ROLE_RANK = {"read": 1, "write": 2, "admin": 3}


def normalize_members(raw: Any) -> list[dict[str, str]]:
    """Bringt beliebige (auch Legacy-)Member-Listen ins kanonische Format.

    - ``["till", "bibs"]``            -> beide als ``write``
    - ``[{"username": "x", "role": "read"}]`` -> unverändert (validiert)
    - gemischte Listen                -> vereinheitlicht
    Unbekannte Rollen fallen auf ``DEFAULT_ROLE`` zurück. Duplikate (gleicher
    username) werden zusammengeführt (letzter Eintrag gewinnt).
    """
    if not isinstance(raw, list):
        return []
    by_name: dict[str, str] = {}
    for entry in raw:
        if isinstance(entry, str):
            name, role = entry, DEFAULT_ROLE
        elif isinstance(entry, dict):
            name = entry.get("username") or ""
            role = entry.get("role") or DEFAULT_ROLE
        else:
            continue
        if not name:
            continue
        if role not in ROLE_RANK:
            role = DEFAULT_ROLE
        by_name[name] = role
    return [{"username": n, "role": r} for n, r in by_name.items()]


def usernames(project: dict) -> list[str]:
    """Reine Namensliste der Members (ohne ``created_by``)."""
    return [m["username"] for m in normalize_members(project.get("members"))]


def role_of(project: dict, username: str) -> str | None:
    """Effektive Rolle eines Users im Projekt, oder ``None`` wenn kein Zugriff.

    ``created_by`` zählt immer als ``admin``.
    """
    if not username:
        return None
    if project.get("created_by") == username:
        return "admin"
    for m in normalize_members(project.get("members")):
        if m["username"] == username:
            return m["role"]
    return None


def has_at_least(role: str | None, required: str) -> bool:
    """True, wenn ``role`` mindestens ``required`` erfüllt (read<write<admin)."""
    if role is None:
        return False
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(required, 99)


def is_member(project: dict, username: str) -> bool:
    """True, wenn der User Zugriff hat (irgendeine Rolle oder created_by)."""
    return role_of(project, username) is not None
