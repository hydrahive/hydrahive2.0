"""Auftrag B2 — Löschprotokoll bei Wegfall/Wiederkehr der Sichtbarkeit von O
(docs/specs/federation-shared-tasks.md §Schalter "Wenn die Sichtbarkeit
wegfällt"). Fälle d, e, g. Fälle a–c stehen in
test_federation_catalog_deletions.py.
"""
from __future__ import annotations

import uuid

from hydrahive.db import federation_catalog as catalog_db
from hydrahive.db import federation_catalog_hub as hub_db
from hydrahive.db import federation_peers as peers_db
from hydrahive.federation.catalog_visibility import origin_visible
from tests._federation_catalog_deletions_helpers import (
    counter,
    deletions_of,
    fingerprint_of,
    item,
    items_of,
    peer,
)

# --- d) Sichtbarkeit von O fällt weg (shared 1 -> 0 im Push) ---------------


def test_d_shared_wegfall_schreibt_loeschzeilen_katalogzeilen_bleiben(client):
    peer_id = peer("origin-d")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t5", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    assert len(items_of(peer_id)) == 1
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=False,
    )
    # Katalogzeile bleibt stehen (Hub zeigt sie im Katalog-Reiter weiter)
    assert len(items_of(peer_id)) == 1
    dels = deletions_of(fingerprint_of(peer_id))
    assert len(dels) == 1 and dels[0]["item_id"] == "t5"


def test_d_origin_visible_prueft_alle_drei_bedingungen():
    assert origin_visible({"catalog_accept": 1, "status": "active"}, {"shared": 1}) is True
    assert origin_visible({"catalog_accept": 0, "status": "active"}, {"shared": 1}) is False
    assert origin_visible({"catalog_accept": 1, "status": "blocked"}, {"shared": 1}) is False
    assert origin_visible({"catalog_accept": 1, "status": "active"}, {"shared": 0}) is False
    assert origin_visible({"catalog_accept": 1, "status": "active"}, None) is False
    assert origin_visible(None, {"shared": 1}) is False


def test_d_catalog_accept_wegnehmen_schreibt_loeschzeilen(client):
    peer_id = peer("origin-d-accept")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t9", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    assert len(items_of(peer_id)) == 1
    catalog_db.set_catalog_accept(peer_id, False)
    assert len(items_of(peer_id)) == 1  # Katalogzeile bleibt
    dels = deletions_of(fingerprint_of(peer_id))
    assert len(dels) == 1 and dels[0]["item_id"] == "t9"


def test_d_partner_sperren_schreibt_loeschzeilen(client):
    peer_id = peer("origin-d-status")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t11", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    assert len(items_of(peer_id)) == 1
    peers_db.set_status(peer_id, "blocked")
    assert len(items_of(peer_id)) == 1  # Katalogzeile bleibt
    dels = deletions_of(fingerprint_of(peer_id))
    assert len(dels) == 1 and dels[0]["item_id"] == "t11"


def test_set_status_unbekannter_peer_gibt_none_zurueck(client):
    assert peers_db.set_status(str(uuid.uuid4()), "blocked") is None


# --- e) Sichtbarkeit kommt wieder -------------------------------------------


def test_e_shared_wiederkehr_vergibt_neue_rev_fuer_alle_eintraege(client):
    peer_id = peer("origin-e")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[
            item("t6", "2026-11-22T00:00:00.000+00:00"),
            item("t7", "2026-11-22T00:00:00.000+00:00"),
        ],
        deleted=[], rejected=[], full_versions=None, shared=True,
    )
    revs_before = {r["item_id"]: r["rev"] for r in items_of(peer_id)}
    hub_db.apply_push(
        peer_id, seq=2, interval_seconds=300, now="2026-11-22T00:00:05.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=False,
    )
    hub_db.apply_push(
        peer_id, seq=3, interval_seconds=300, now="2026-11-22T00:00:10.000+00:00",
        items=[], deleted=[], rejected=[], full_versions=None, shared=True,
    )
    revs_after = {r["item_id"]: r["rev"] for r in items_of(peer_id)}
    assert revs_after["t6"] > revs_before["t6"]
    assert revs_after["t7"] > revs_before["t7"]


def test_e_catalog_accept_wiedergeben_vergibt_neue_rev(client):
    peer_id = peer("origin-e-accept")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t10", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    rev_before = items_of(peer_id)[0]["rev"]
    catalog_db.set_catalog_accept(peer_id, False)
    catalog_db.set_catalog_accept(peer_id, True)
    rev_after = items_of(peer_id)[0]["rev"]
    assert rev_after > rev_before


def test_e_partner_wieder_aktivieren_vergibt_neue_rev(client):
    peer_id = peer("origin-e-status")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t12", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    rev_before = items_of(peer_id)[0]["rev"]
    peers_db.set_status(peer_id, "blocked")
    peers_db.set_status(peer_id, "active")
    rev_after = items_of(peer_id)[0]["rev"]
    assert rev_after > rev_before


# --- g) Hub schaltet sein eigenes "shared" aus: KEINE Löschzeilen ----------


def test_g_hub_shared_aus_schreibt_keine_loeschzeilen_fuer_partner_oder_eigene(client, admin_headers):
    """Bestellt: PUT /api/federation/catalog/settings mit shared=false auf dem
    Hub selbst darf weder für Partner-Einträge (O) noch für eigene Einträge
    Löschzeilen schreiben — V2 lehnt catalog_pull dann einfach ab, Clients
    leeren ihre Kopie selbst (Spec: "Bedingung 1 fällt weg")."""
    peer_id = peer("origin-g")
    hub_db.apply_push(
        peer_id, seq=1, interval_seconds=300, now="2026-11-22T00:00:00.000+00:00",
        items=[item("t8", "2026-11-22T00:00:00.000+00:00")], deleted=[], rejected=[],
        full_versions=None, shared=True,
    )
    assert len(items_of(peer_id)) == 1
    before = counter()

    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json={"enabled": True, "interval_seconds": 300, "users": [], "excluded_projects": [], "shared": True},
    )
    assert r.status_code == 200, r.text
    r2 = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json={"enabled": True, "interval_seconds": 300, "users": [], "excluded_projects": [], "shared": False},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["shared"] is False

    assert len(items_of(peer_id)) == 1  # Partner-Katalogzeile unangetastet
    assert deletions_of(fingerprint_of(peer_id)) == []  # keine Löschzeile für O
    assert counter() == before  # gar keine neue rev vergeben (Hub-eigenes shared betrifft apply_push nicht)
