"""Gemeinsame Helfer für test_federation_catalog_deletions.py und
test_federation_catalog_visibility.py (Auftrag B2/B3, kein eigenes
``test_``-Präfix, pytest sammelt diese Datei daher nicht als Testdatei)."""
from __future__ import annotations

import uuid

from hydrahive.db.connection import db


def peer(name: str, *, status: str = "active", catalog_accept: bool = True) -> str:
    peer_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_peers "
            "(id, name, url, public_key, fingerprint, status, catalog_accept, created_at) "
            "VALUES (?, ?, 'https://x', ?, ?, ?, ?, 'now')",
            (peer_id, name, peer_id, peer_id, status, 1 if catalog_accept else 0),
        )
    return peer_id


def item(item_id: str, updated_at: str, owner: str = "till") -> dict:
    return {
        "kind": "task", "item_id": item_id, "owner": owner, "title": "T",
        "status": "open", "priority": None, "project_id": None, "project_name": None,
        "created_at": None, "updated_at": updated_at,
    }


def items_of(peer_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def deletions_of(origin_fp: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_deletions WHERE origin_fp = ? ORDER BY rev", (origin_fp,),
        ).fetchall()
    return [dict(r) for r in rows]


def counter() -> int:
    with db() as conn:
        return int(conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()[0])


def fingerprint_of(peer_id: str) -> str:
    with db() as conn:
        return conn.execute(
            "SELECT fingerprint FROM federation_peers WHERE id = ?", (peer_id,),
        ).fetchone()["fingerprint"]
