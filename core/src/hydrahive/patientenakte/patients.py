"""Patient-Stammdaten — CRUD mit Owner-Isolation."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

_JSON_FIELDS = {"adresse": "adresse_json", "telefon": "telefon_json",
                "notfallkontakt": "notfallkontakt_json", "versicherung": "versicherung_json"}
_SCALAR = ("slug", "name", "vorname", "geburtsdatum", "geburtsort", "geschlecht",
           "blutgruppe", "rh_faktor", "email", "beruf", "arbeitgeber", "external_id")


def create(user_id: str, data: dict[str, Any]) -> str:
    pid = uuid7()
    ts = now_iso()
    cols = ["id", "owner_user_id", "created_at", "updated_at"]
    vals: list[Any] = [pid, user_id, ts, ts]
    for f in _SCALAR:
        if f in data:
            cols.append(f)
            vals.append(data[f])
    for f, col in _JSON_FIELDS.items():
        if f in data:
            cols.append(col)
            vals.append(json.dumps(data[f]))
    ph = ",".join("?" * len(cols))
    with db() as conn:
        conn.execute(f"INSERT INTO akte_patient ({','.join(cols)}) VALUES ({ph})", vals)
    return pid


def _row_to_patient(row) -> dict[str, Any]:
    out = {k: row[k] for k in row.keys() if not k.endswith("_json")}
    for f, col in _JSON_FIELDS.items():
        if row[col]:
            out[f] = json.loads(row[col])
    return out


def get(user_id: str, pid: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM akte_patient WHERE id=? AND owner_user_id=?", (pid, user_id)
        ).fetchone()
    return _row_to_patient(row) if row else None


def list_for(user_id: str) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM akte_patient WHERE owner_user_id=? ORDER BY slug", (user_id,)
        ).fetchall()
    return [_row_to_patient(r) for r in rows]


def update(user_id: str, pid: str, data: dict[str, Any]) -> bool:
    sets, vals = ["updated_at=?"], [now_iso()]
    for f in _SCALAR:
        if f in data:
            sets.append(f"{f}=?")
            vals.append(data[f])
    for f, col in _JSON_FIELDS.items():
        if f in data:
            sets.append(f"{col}=?")
            vals.append(json.dumps(data[f]))
    vals += [pid, user_id]
    with db() as conn:
        cur = conn.execute(
            f"UPDATE akte_patient SET {','.join(sets)} WHERE id=? AND owner_user_id=?", vals)
    return cur.rowcount > 0


def delete(user_id: str, pid: str) -> bool:
    with db() as conn:
        cur = conn.execute(
            "DELETE FROM akte_patient WHERE id=? AND owner_user_id=?", (pid, user_id))
    return cur.rowcount > 0
