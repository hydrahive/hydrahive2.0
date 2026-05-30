"""Aggregierte Sichten: Timeline + Summary über alle Entitäten."""
from __future__ import annotations

from typing import Any

from hydrahive.db.connection import db
from hydrahive.patientenakte.entities import _row_to_dict
from hydrahive.patientenakte.patients import get as _get_patient
from hydrahive.patientenakte.schema import ENTITIES


def summary(user_id: str, pid: str) -> dict[str, int]:
    if _get_patient(user_id, pid) is None:
        raise PermissionError(pid)
    out: dict[str, int] = {}
    with db() as conn:
        for key, spec in ENTITIES.items():
            row = conn.execute(
                f"SELECT COUNT(*) AS c FROM {spec.table} WHERE patient_id=?", (pid,)).fetchone()
            out[key] = row["c"]
    return out


def timeline(user_id: str, pid: str) -> list[dict[str, Any]]:
    if _get_patient(user_id, pid) is None:
        raise PermissionError(pid)
    entries: list[dict[str, Any]] = []
    with db() as conn:
        for key, spec in ENTITIES.items():
            rows = conn.execute(
                f"SELECT * FROM {spec.table} WHERE patient_id=? AND sort_date IS NOT NULL",
                (pid,)).fetchall()
            for r in rows:
                entries.append({"entity": key, "label": spec.label,
                                "sort_date": r["sort_date"], "record": _row_to_dict(spec, r)})
    entries.sort(key=lambda e: e["sort_date"], reverse=True)
    return entries
