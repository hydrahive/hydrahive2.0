"""Auftrag B2 — Löschprotokoll für Einträge von Partnern (Ursprung O)
(docs/specs/federation-shared-tasks.md §Schalter "Wenn die Sichtbarkeit
wegfällt", §Änderungsnummer).

Fälle a–e, g (Aufräumen nach 7 Tagen, Ausschluss beim Hub, Vormerkung eigener
Hub-Einträge folgen in B3, hier nicht getestet).
"""
from __future__ import annotations

import uuid

from hydrahive.db import federation_catalog_hub as hub_db
from hydrahive.db import federation_peers as peers_db
from hydrahive.db.connection import db
from hydrahive.federation.catalog_visibility import origin_visible


def _peer(name: str, *, status: str = "active", catalog_accept: bool = True) -> str:
    peer_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_peers "
            "(id, name, url, public_key, fingerprint, status, catalog_accept, created_at) "
            "VALUES (?, ?, 'https://x', ?, ?, ?, ?, 'now')",
            (peer_id, name, peer_id, peer_id, status, 1 if catalog_accept else 0),
        )
    return peer_id


def _item(item_id: str, updated_at: str, owner: str = "till") -> dict:
    return {
        "kind": "task", "item_id": item_id, "owner": owner, "title": "T",
        "status": "open", "priority": None, "project_id": None, "project_name": None,
        "created_at": None, "updated_at": updated_at,
    }


def _items(peer_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def _deletions(origin_fp: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_deletions WHERE origin_fp = ? ORDER BY rev", (origin_fp,),
        ).fetchall()
    return [dict(r) for r in rows]


def _counter() -> int:
    with db() as conn:
        return int(conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()[0])


def _fp(peer_id: str) -> str:
    with db() as conn:
        return conn.execute(
            "SELECT fingerprint FROM federation_peers WHERE id = ?", (peer_id,),
        ).fetchone()["fingerprint"]


# --- a) Push mit "deleted" --------------------------------------------------

def test_a_push_mit_deleted_schreibt_loeschzeile(client):
    peer_id = _peer("origin-a")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("t1", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    item_rev = _items(peer_id)[0]["rev"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[("task", "t1")], rejected=[], full_versions=None,
    )
    assert _items(peer_id) == []  # Katalogzeile ist weg
    dels = _deletions(_fp(peer_id))
    assert len(dels) == 1
    assert dels[0]["kind"] == "task" and dels[0]["item_id"] == "t1" and dels[0]["owner"] == "till"
    assert dels[0]["rev"] > item_rev  # rev steigt gemeinsam mit den items


# --- b) Abgleich (_reconcile) ----------------------------------------------

def test_b_abgleich_entfernt_fehlendes_und_schreibt_loeschzeile(client):
    peer_id = _peer("origin-b")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("t2", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    item_rev = _items(peer_id)[0]["rev"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[],
        full_versions={("till", "task"): {}},  # t2 fehlt in der Versionsliste
    )
    assert _items(peer_id) == []
    dels = _deletions(_fp(peer_id))
    assert len(dels) == 1
    assert dels[0]["item_id"] == "t2"
    assert dels[0]["rev"] > item_rev


# --- c) Partner entfernen ---------------------------------------------------

def test_c_partner_entfernen_schreibt_loeschzeilen_fuer_alle_katalogzeilen(client):
    peer_id = _peer("origin-c")
    origin_fp = _fp(peer_id)
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[
            _item("t3", "2026-11-22T00:00:00.000+00:00"),
            _item("t4", "2026-11-22T00:00:00.000+00:00"),
        ],
        deleted=[], rejected=[], full_versions=None,
    )
    assert len(_items(peer_id)) == 2

    ok = peers_db.delete_peer(peer_id)
    assert ok is True

    with db() as conn:
        assert conn.execute(
            "SELECT 1 FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
        ).fetchone() is None  # CASCADE hat die Katalogzeilen entfernt

    dels = _deletions(origin_fp)
    assert {d["item_id"] for d in dels} == {"t3", "t4"}
    revs_ = [d["rev"] for d in dels]
    assert len(set(revs_)) == 2  # je eigene rev, eindeutig


def test_c_partner_ohne_katalogzeilen_schreibt_nichts(client):
    peer_id = _peer("origin-c-leer")
    before = _counter()
    assert peers_db.delete_peer(peer_id) is True
    assert _counter() == before  # kein next_rev() ohne Katalogzeilen


# --- d) Sichtbarkeit von O fällt weg (shared 1 -> 0 im Push) ---------------

def test_d_shared_wegfall_schreibt_loeschzeilen_katalogzeilen_bleiben(client):
    peer_id = _peer("origin-d")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("t5", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    assert len(_items(peer_id)) == 1
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=False,
    )
    # Katalogzeile bleibt stehen (Hub zeigt sie im Katalog-Reiter weiter)
    assert len(_items(peer_id)) == 1
    dels = _deletions(_fp(peer_id))
    assert len(dels) == 1 and dels[0]["item_id"] == "t5"


def test_d_origin_visible_prueft_alle_drei_bedingungen():
    assert origin_visible({"catalog_accept": 1, "status": "active"}, {"shared": 1}) is True
    assert origin_visible({"catalog_accept": 0, "status": "active"}, {"shared": 1}) is False
    assert origin_visible({"catalog_accept": 1, "status": "blocked"}, {"shared": 1}) is False
    assert origin_visible({"catalog_accept": 1, "status": "active"}, {"shared": 0}) is False
    assert origin_visible({"catalog_accept": 1, "status": "active"}, None) is False
    assert origin_visible(None, {"shared": 1}) is False


# --- e) Sichtbarkeit kommt wieder -------------------------------------------

def test_e_shared_wiederkehr_vergibt_neue_rev_fuer_alle_eintraege(client):
    peer_id = _peer("origin-e")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[
            _item("t6", "2026-11-22T00:00:00.000+00:00"),
            _item("t7", "2026-11-22T00:00:00.000+00:00"),
        ],
        deleted=[], rejected=[], full_versions=None, shared=True,
    )
    revs_before = {r["item_id"]: r["rev"] for r in _items(peer_id)}
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=False,
    )
    hub_db.apply_push(
        peer_id, seq=3, interval_seconds=300, now="2026-11-22T00:00:10.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=True,
    )
    revs_after = {r["item_id"]: r["rev"] for r in _items(peer_id)}
    assert revs_after["t6"] > revs_before["t6"]
    assert revs_after["t7"] > revs_before["t7"]


# --- g) Hub schaltet sein eigenes "shared" aus: keine Löschzeilen ----------

def test_g_hub_shared_aus_schreibt_keine_loeschzeilen():
    """Diese Funktion (apply_push) kennt nur Partner-Sichtbarkeit (O). Das
    eigene shared des Hubs wirkt in catalog_pull (V2) und bei der eigenen
    Vormerkung (B3) — hier nur: ein stinknormaler Push ohne Sichtbarkeits-
    wechsel von O schreibt nie Löschzeilen für O."""
    peer_id = _peer("origin-g")
    before = _counter()
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[_item("t8", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=True,
    )
    assert _deletions(_fp(peer_id)) == []
    assert _counter() > before  # nur durch das Upsert, nicht durch Löschzeilen
