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
    # Migration 018 added verify_tls; in case anyone reads the row
    # before migrate ran, normalize to 1 (verify-by-default).
    if "verify_tls" not in d or d["verify_tls"] is None:
        d["verify_tls"] = 1
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


def create_workstation(
    name: str,
    url: str,
    token: str = "",
    enabled: bool = True,
    verify_tls: bool = True,
) -> dict:
    """Create a workstation row.

    verify_tls: when False, the registry's httpx client uses verify=False
    for card-fetch + remote_chat against this peer. Use for self-signed
    LAN/Tailnet workstations. Default True (safe).
    """
    ws_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_workstations "
            "(id, name, url, token, enabled, verify_tls) VALUES (?,?,?,?,?,?)",
            (ws_id, name, url.rstrip("/"), token, int(enabled), int(verify_tls)),
        )
    return get_workstation(ws_id)  # type: ignore[return-value]


def update_workstation(ws_id: str, **fields: Any) -> dict | None:
    # verify_tls joined the allow-list so the UI/API can toggle it.
    allowed = {"name", "url", "token", "enabled", "verify_tls"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_workstation(ws_id)
    if "url" in updates:
        updates["url"] = updates["url"].rstrip("/")
    # Coerce bool→int for SQLite (enabled/verify_tls)
    for k in ("enabled", "verify_tls"):
        if k in updates and isinstance(updates[k], bool):
            updates[k] = int(updates[k])
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
            "UPDATE federation_workstations SET card_json = ?, "
            "last_seen = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            (card_json, ws_id),
        )


def delete_workstation(ws_id: str) -> bool:
    with db() as conn:
        cur = conn.execute(
            "DELETE FROM federation_workstations WHERE id = ?", (ws_id,)
        )
    return cur.rowcount > 0
