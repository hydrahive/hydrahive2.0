"""DB-Operationen für Federation-Workstations."""
from __future__ import annotations

import json
import uuid
from typing import Any

from hydrahive.db.connection import db


def _row(r: Any) -> dict:
    d = dict(r)
    if d.get("card_json"):
        try:
            d["card"] = json.loads(d["card_json"])
        except Exception:
            d["card"] = None
    else:
        d["card"] = None
    return d


def list_workstations() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_workstations ORDER BY name"
        ).fetchall()
    return [_row(r) for r in rows]


def get_workstation(ws_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM federation_workstations WHERE id = ?", (ws_id,)
        ).fetchone()
    return _row(row) if row else None


def get_by_name(name: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM federation_workstations WHERE LOWER(name) = LOWER(?)",
            (name,),
        ).fetchone()
    return _row(row) if row else None


def create_workstation(name: str, url: str, token: str = "", enabled: bool = True) -> dict:
    ws_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_workstations (id, name, url, token, enabled) VALUES (?,?,?,?,?)",
            (ws_id, name, url.rstrip("/"), token, int(enabled)),
        )
    return get_workstation(ws_id)  # type: ignore[return-value]


def update_workstation(ws_id: str, **fields: Any) -> dict | None:
    allowed = {"name", "url", "token", "enabled"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_workstation(ws_id)
    if "url" in updates:
        updates["url"] = updates["url"].rstrip("/")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [ws_id]
    with db() as conn:
        conn.execute(
            f"UPDATE federation_workstations SET {set_clause} WHERE id = ?", values
        )
    return get_workstation(ws_id)


def update_card(ws_id: str, card_json: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE federation_workstations SET card_json = ?, last_seen = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            (card_json, ws_id),
        )


def delete_workstation(ws_id: str) -> bool:
    with db() as conn:
        cur = conn.execute(
            "DELETE FROM federation_workstations WHERE id = ?", (ws_id,)
        )
    return cur.rowcount > 0
