"""Generischer CRUD über alle Akte-Entitäten — registry-getrieben.

Tabellen-/Spaltennamen stammen ausschließlich aus der statischen ENTITIES-
Registry (nie aus User-Input) — keine SQL-Injection-Fläche über die
f-String-Interpolation. Werte gehen immer über Parameter-Bindings.

Schreibpfade (create/batch) laufen in einer BEGIN-IMMEDIATE-Transaktion:
das serialisiert gleichzeitige Schreiber (kein TOCTOU bei external_id-Upsert)
und macht Batch-Importe atomar (alles-oder-nichts).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from ._dates import to_sort_date
from .patients import get as _get_patient
from .schema import COMMON_FIELDS, ENTITIES, EntitySpec


def _spec(entity: str) -> EntitySpec:
    if entity not in ENTITIES:
        raise KeyError(entity)
    return ENTITIES[entity]


def _ensure_owner(user_id: str, pid: str) -> None:
    if _get_patient(user_id, pid) is None:
        raise PermissionError(pid)


def _split(spec: EntitySpec, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    typed = {f: data[f] for f in spec.fields if f in data}
    extra = {f: data[f] for f in spec.array_fields if f in data}
    for f in COMMON_FIELDS:
        if f in data:
            typed[f] = data[f]
    if "verifiziert" in typed:
        typed["verifiziert"] = int(bool(typed["verifiziert"]))
    return typed, extra


def _sort_date_for(spec: EntitySpec, data: dict[str, Any]) -> str | None:
    return to_sort_date(data.get(spec.date_field)) if spec.date_field else None


def _insert(conn: sqlite3.Connection, spec: EntitySpec, pid: str,
            typed: dict[str, Any], extra: dict[str, Any], data: dict[str, Any], ts: str) -> str:
    eid = uuid7()
    cols = ["id", "patient_id", "created_at", "updated_at", "extra_json", "sort_date"]
    vals: list[Any] = [eid, pid, ts, ts,
                       json.dumps(extra) if extra else None, _sort_date_for(spec, data)]
    for k, v in typed.items():
        cols.append(k)
        vals.append(v)
    ph = ",".join("?" * len(cols))
    conn.execute(f"INSERT INTO {spec.table} ({','.join(cols)}) VALUES ({ph})", vals)
    return eid


def _update(conn: sqlite3.Connection, spec: EntitySpec, eid: str, pid: str,
            typed: dict[str, Any], extra: dict[str, Any], data: dict[str, Any], ts: str) -> bool:
    sets, vals = ["updated_at=?"], [ts]
    for k, v in typed.items():
        sets.append(f"{k}=?")
        vals.append(v)
    if extra:
        sets.append("extra_json=?")
        vals.append(json.dumps(extra))
    if spec.date_field and spec.date_field in data:
        sets.append("sort_date=?")
        vals.append(_sort_date_for(spec, data))
    vals += [eid, pid]
    cur = conn.execute(
        f"UPDATE {spec.table} SET {','.join(sets)} WHERE id=? AND patient_id=?", vals)
    return cur.rowcount > 0


def _upsert(conn: sqlite3.Connection, spec: EntitySpec, pid: str, data: dict[str, Any]) -> str:
    typed, extra = _split(spec, data)
    ts = now_iso()
    ext = typed.get("external_id")
    if ext:
        row = conn.execute(
            f"SELECT id FROM {spec.table} WHERE patient_id=? AND external_id=?", (pid, ext)
        ).fetchone()
        if row:
            _update(conn, spec, row["id"], pid, typed, extra, data, ts)
            return row["id"]
    return _insert(conn, spec, pid, typed, extra, data, ts)


def _row_to_dict(spec: EntitySpec, row) -> dict[str, Any]:
    out = {k: row[k] for k in row.keys() if k != "extra_json"}
    if row["extra_json"]:
        out.update(json.loads(row["extra_json"]))
    return out


def create(user_id: str, pid: str, entity: str, data: dict[str, Any]) -> str:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    with db(immediate=True) as conn:
        return _upsert(conn, spec, pid, data)


def batch_create(user_id: str, pid: str, entity: str, items: list[dict[str, Any]]) -> int:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    with db(immediate=True) as conn:
        for item in items:
            _upsert(conn, spec, pid, item)
    return len(items)


def list_for(user_id: str, pid: str, entity: str, *, q: str | None = None,
             status: str | None = None) -> list[dict[str, Any]]:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    sql = f"SELECT * FROM {spec.table} WHERE patient_id=?"
    args: list[Any] = [pid]
    if status and "status" in spec.fields:
        sql += " AND status=?"
        args.append(status)
    if q:
        like = " OR ".join(f"{f} LIKE ?" for f in spec.fields)
        sql += f" AND ({like})"
        args += [f"%{q}%"] * len(spec.fields)
    sql += " ORDER BY sort_date DESC NULLS LAST, created_at DESC"
    with db() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [_row_to_dict(spec, r) for r in rows]


def get(user_id: str, pid: str, entity: str, eid: str) -> dict[str, Any] | None:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    with db() as conn:
        row = conn.execute(
            f"SELECT * FROM {spec.table} WHERE id=? AND patient_id=?", (eid, pid)).fetchone()
    return _row_to_dict(spec, row) if row else None


def update(user_id: str, pid: str, entity: str, eid: str, data: dict[str, Any]) -> bool:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    typed, extra = _split(spec, data)
    with db() as conn:
        return _update(conn, spec, eid, pid, typed, extra, data, now_iso())


def delete(user_id: str, pid: str, entity: str, eid: str) -> bool:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    with db() as conn:
        cur = conn.execute(
            f"DELETE FROM {spec.table} WHERE id=? AND patient_id=?", (eid, pid))
    return cur.rowcount > 0
