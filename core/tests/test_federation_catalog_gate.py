"""Q1 — Schalter für ctx.catalog_changed über die echten Routen
(docs/specs/federation-catalog.md §Katalog-Quellen: „Ist Federation aus oder
kein Hub gesetzt, passiert nichts“).

Vorgemerkt wird nur bei Sync `enabled` + ausgewähltem Nutzer + aktivem Hub.
Hub abwählen, Partner sperren oder löschen schaltet sofort ab und leert die Liste.
"""
from __future__ import annotations

import pytest

from hydrahive.federation import catalog_changes
from hydrahive.modules.context import ModuleContext
from tests._own_rows import only_own_rows
from tests.test_federation_catalog_e1 import CATALOG_TABLES, _add_active_peer, _cleanup, _settings_body


@pytest.fixture(autouse=True)
def _clean(client, admin_headers):
    _cleanup(client, admin_headers)
    catalog_changes._reset_for_tests()
    with only_own_rows(*CATALOG_TABLES):
        yield
    _cleanup(client, admin_headers)
    catalog_changes._reset_for_tests()


def _touch() -> int:
    ModuleContext("tasks").catalog_changed("task", "testuser", "t-1")
    return catalog_changes.pending_count()


def _settings(client, admin_headers, **over):
    r = client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(**over))
    assert r.status_code == 200, r.text


def _hub(client, admin_headers, peer_id: str, on: bool):
    r = client.put(f"/api/federation/peers/{peer_id}/hub", headers=admin_headers, json={"is_hub": on})
    assert r.status_code == 200, r.text


def test_ohne_hub_nichts_vorgemerkt(client, admin_headers):
    _settings(client, admin_headers)
    assert catalog_changes.refresh_gate() is False
    assert _touch() == 0


def test_hub_aber_sync_aus_nichts_vorgemerkt(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    _settings(client, admin_headers, enabled=False)
    _hub(client, admin_headers, peer["id"], True)
    assert catalog_changes.gate_active() is False
    assert _touch() == 0


def test_hub_aber_keine_nutzer_nichts_vorgemerkt(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    _settings(client, admin_headers, users=[])
    _hub(client, admin_headers, peer["id"], True)
    assert catalog_changes.gate_active() is False
    assert _touch() == 0


def test_aktiv_merkt_vor_und_hub_abwaehlen_leert(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    _settings(client, admin_headers)
    _hub(client, admin_headers, peer["id"], True)
    assert catalog_changes.gate_active() is True
    assert _touch() == 1
    _hub(client, admin_headers, peer["id"], False)
    assert catalog_changes.gate_active() is False
    assert catalog_changes.pending_count() == 0
    assert _touch() == 0


def test_partner_sperren_schaltet_ab(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    _settings(client, admin_headers)
    _hub(client, admin_headers, peer["id"], True)
    assert _touch() == 1
    r = client.post(f"/api/federation/peers/{peer['id']}/block", headers=admin_headers)
    assert r.status_code == 200
    assert catalog_changes.gate_active() is False
    assert _touch() == 0


def test_partner_loeschen_schaltet_ab(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    _settings(client, admin_headers)
    _hub(client, admin_headers, peer["id"], True)
    r = client.delete(f"/api/federation/peers/{peer['id']}", headers=admin_headers)
    assert r.status_code == 204
    assert catalog_changes.gate_active() is False
    assert _touch() == 0


def test_sync_ausschalten_schaltet_ab(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    _settings(client, admin_headers)
    _hub(client, admin_headers, peer["id"], True)
    assert _touch() == 1
    _settings(client, admin_headers, enabled=False)
    assert catalog_changes.gate_active() is False
    assert catalog_changes.pending_count() == 0
