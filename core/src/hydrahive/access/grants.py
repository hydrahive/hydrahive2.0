"""Funktions-Freigaben (Spec access-groups §6/§7).

Eine Freigabe verbindet eine Funktion mit einem Subjekt (Nutzer, Gruppe oder
alle) und einer Stufe. Schreiben darf nur der Admin, das prüft die Route.
Jede tatsächliche Änderung schreibt einen Audit-Eintrag mit Ziel ``cap:<id>``.
"""
from __future__ import annotations

from hydrahive.access.store import audit
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

SUBJECT_TYPES = ("user", "group", "everyone")
LEVELS = ("use", "manage")
LEVEL_RANK = {"use": 1, "manage": 2}


def _validate(subject_type: str, subject_id: str, level: str | None = None) -> None:
    if subject_type not in SUBJECT_TYPES:
        raise ValueError(f"unbekannter subject_type {subject_type!r}")
    if subject_type == "everyone" and subject_id:
        raise ValueError("subject_id muss bei 'everyone' leer sein")
    if subject_type != "everyone" and not subject_id:
        raise ValueError("subject_id fehlt")
    if level is not None and level not in LEVELS:
        raise ValueError(f"unbekannte Stufe {level!r}")


def grant(capability: str, subject_type: str, subject_id: str, level: str, *, actor_id: str) -> None:
    _validate(subject_type, subject_id, level)
    with db() as c:
        c.execute(
            "INSERT INTO access_capability_grants "
            "(capability, subject_type, subject_id, level, granted_by, granted_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(capability, subject_type, subject_id) DO UPDATE SET "
            "level = excluded.level, granted_by = excluded.granted_by, granted_at = excluded.granted_at",
            (capability, subject_type, subject_id, level, actor_id, now_iso()),
        )
        audit(c, actor_id, "grant", f"cap:{capability}", f"{subject_type}:{subject_id}={level}")


def revoke(capability: str, subject_type: str, subject_id: str, *, actor_id: str) -> None:
    _validate(subject_type, subject_id)
    with db() as c:
        cur = c.execute(
            "DELETE FROM access_capability_grants "
            "WHERE capability = ? AND subject_type = ? AND subject_id = ?",
            (capability, subject_type, subject_id),
        )
        if cur.rowcount:
            audit(c, actor_id, "revoke", f"cap:{capability}", f"{subject_type}:{subject_id}")


def grants_for(capability: str) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT capability, subject_type, subject_id, level FROM access_capability_grants "
            "WHERE capability = ? ORDER BY subject_type, subject_id",
            (capability,),
        ).fetchall()
    return [dict(r) for r in rows]


def all_grants() -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT capability, subject_type, subject_id, level FROM access_capability_grants "
            "ORDER BY capability, subject_type, subject_id"
        ).fetchall()
    return [dict(r) for r in rows]


def grants_matching(*, user_id: str, group_ids: list[str]) -> list[dict]:
    """Alle Freigaben, die auf diesen Nutzer zutreffen: everyone, er selbst, seine Gruppen."""
    params: list[str] = [user_id]
    group_clause = ""
    if group_ids:
        group_clause = f" OR (subject_type = 'group' AND subject_id IN ({','.join('?' * len(group_ids))}))"
        params.extend(group_ids)
    with db() as c:
        rows = c.execute(
            "SELECT capability, subject_type, subject_id, level FROM access_capability_grants "
            "WHERE subject_type = 'everyone' OR (subject_type = 'user' AND subject_id = ?)"
            + group_clause,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def purge_subject(conn, subject_type: str, subject_id: str) -> int:
    """Entfernt alle Freigaben eines Subjekts (für das Löschen von Nutzern/Gruppen)."""
    return conn.execute(
        "DELETE FROM access_capability_grants WHERE subject_type = ? AND subject_id = ?",
        (subject_type, subject_id),
    ).rowcount
