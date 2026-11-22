"""Auftrag B2 — Löschprotokoll für Einträge von Partnern (Ursprung O)
(docs/specs/federation-shared-tasks.md §Änderungsnummer).

Fälle a–c (Push mit deleted, Abgleich, Partner entfernen). Fälle d/e/g
(Sichtbarkeit) stehen in test_federation_catalog_visibility.py — dort auch
die Hilfsfunktionen aus _federation_catalog_deletions_helpers.py.
"""
from __future__ import annotations

from hydrahive.db import federation_catalog_hub as hub_db
from hydrahive.db import federation_peers as peers_db
from hydrahive.db.connection import db
from tests._federation_catalog_deletions_helpers import (
    counter,
    deletions_of,
    fingerprint_of,
    item,
    items_of,
    peer,
)

# --- a) Push mit "deleted" --------------------------------------------------


def test_a_push_mit_deleted_schreibt_loeschzeile(client):
    peer_id = peer("origin-a")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t1", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    item_rev = items_of(peer_id)[0]["rev"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[("task", "t1")], rejected=[], full_versions=None,
    )
    assert items_of(peer_id) == []  # Katalogzeile ist weg
    dels = deletions_of(fingerprint_of(peer_id))
    assert len(dels) == 1
    assert dels[0]["kind"] == "task" and dels[0]["item_id"] == "t1" and dels[0]["owner"] == "till"
    assert dels[0]["rev"] > item_rev  # rev steigt gemeinsam mit den items


# --- b) Abgleich (_reconcile) ----------------------------------------------


def test_b_abgleich_entfernt_fehlendes_und_schreibt_loeschzeile(client):
    peer_id = peer("origin-b")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t2", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[], full_versions=None,
    )
    item_rev = items_of(peer_id)[0]["rev"]
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[],
        full_versions={("till", "task"): {}},  # t2 fehlt in der Versionsliste
    )
    assert items_of(peer_id) == []
    dels = deletions_of(fingerprint_of(peer_id))
    assert len(dels) == 1
    assert dels[0]["item_id"] == "t2"
    assert dels[0]["rev"] > item_rev


# --- c) Partner entfernen ---------------------------------------------------


def test_c_partner_entfernen_schreibt_loeschzeilen_fuer_alle_katalogzeilen(client):
    peer_id = peer("origin-c")
    origin_fp = fingerprint_of(peer_id)
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[
            item("t3", "2026-11-22T00:00:00.000+00:00"),
            item("t4", "2026-11-22T00:00:00.000+00:00"),
        ],
        deleted=[], rejected=[], full_versions=None,
    )
    assert len(items_of(peer_id)) == 2

    ok = peers_db.delete_peer(peer_id)
    assert ok is True

    with db() as conn:
        assert conn.execute(
            "SELECT 1 FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
        ).fetchone() is None  # CASCADE hat die Katalogzeilen entfernt

    dels = deletions_of(origin_fp)
    assert {d["item_id"] for d in dels} == {"t3", "t4"}
    revs_ = [d["rev"] for d in dels]
    assert len(set(revs_)) == 2  # je eigene rev, eindeutig


def test_c_partner_ohne_katalogzeilen_schreibt_nichts(client):
    peer_id = peer("origin-c-leer")
    before = counter()
    assert peers_db.delete_peer(peer_id) is True
    assert counter() == before  # kein next_rev() ohne Katalogzeilen
