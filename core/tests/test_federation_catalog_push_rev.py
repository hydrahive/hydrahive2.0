"""Auftrag B, Stück 1 — rev bei jedem Upsert in apply_push
(docs/specs/federation-shared-tasks.md §Änderungsnummer).

Jedes angenommene Upsert (auch bei updated_at-Gleichstand, der übernommen
wird) bekommt die nächste rev. Abgelehnte oder ältere Upserts (updated_at <
gespeichert) vergeben keine rev.
"""
from __future__ import annotations

import uuid

from hydrahive.db import federation_catalog_hub as hub_db
from hydrahive.db.connection import db


def _peer(client) -> str:
    peer_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at) "
            "VALUES (?, ?, 'https://x', ?, ?, 'active', 'now')",
            (peer_id, f"hub-rev-test-{peer_id}", peer_id, peer_id),
        )
    return peer_id


def _item(item_id: str, updated_at: str) -> dict:
    return {
        "kind": "task", "item_id": item_id, "owner": "till", "title": "T",
        "status": "open", "priority": None, "project_id": None, "project_name": None,
        "created_at": None, "updated_at": updated_at,
    }


def _revs(peer_id: str) -> dict[str, int]:
    with db() as conn:
        rows = conn.execute(
            "SELECT item_id, rev FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
        ).fetchall()
    return {r["item_id"]: r["rev"] for r in rows}


def _counter() -> int:
    with db() as conn:
        return int(conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()[0])


def test_jeder_upsert_bekommt_steigende_eindeutige_rev(client):
    peer_id = _peer(client)
    before = _counter()
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("a", "2026-11-22T00:00:00.000+00:00"), _item("b", "2026-11-22T00:00:00.000+00:00")],
        deleted=[], rejected=[], full_versions=None,
    )
    revs = _revs(peer_id)
    assert revs["a"] > before and revs["b"] > before
    assert revs["a"] != revs["b"]


def test_updated_at_gleichstand_wird_uebernommen_und_bekommt_neue_rev(client):
    peer_id = _peer(client)
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("c", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    rev1 = _revs(peer_id)["c"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:01.000+00:00",
        items=[_item("c", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    rev2 = _revs(peer_id)["c"]
    assert rev2 > rev1  # Gleichstand wird übernommen (WHERE excluded >= gespeichert), neue rev


def test_aelterer_upsert_vergibt_keine_neue_rev(client):
    peer_id = _peer(client)
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("d", "2026-11-22T00:00:05.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    rev1 = _revs(peer_id)["d"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:10.000+00:00",
        items=[_item("d", "2026-11-22T00:00:01.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    rev2 = _revs(peer_id)["d"]
    assert rev1 == rev2  # älterer updated_at wurde verworfen, keine neue rev


def test_zaehler_gemeinsam_ueber_mehrere_pushes_streng_steigend(client):
    peer_id = _peer(client)
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("e", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    rev_e = _revs(peer_id)["e"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:01.000+00:00",
        items=[_item("f", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    rev_f = _revs(peer_id)["f"]
    assert rev_f > rev_e
