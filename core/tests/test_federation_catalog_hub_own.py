"""Auftrag B3, Stück 2 — Vormerkung eigener Hub-Einträge mit shared
(docs/specs/federation-shared-tasks.md §Änderungsnummer "Eigene Einträge des
Hubs").

Zwei Dinge getrennt getestet: (1) `catalog_changes` merkt Hub-Einträge nur
vor, wenn diese Instanz selbst Hub mit `shared` ist, OHNE den Client-Push
(`drain()`) zu berühren. (2) `catalog_hub_own.hub_distribute_step()` prüft
vorgemerkte Einträge gegen die Quelle und schreibt Löschzeilen für
Fehlendes/Ausgeschlossenes.
"""
from __future__ import annotations

import uuid

import pytest

from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db.connection import db
from hydrahive.federation import catalog_changes
from hydrahive.federation import catalog_hub_own as hub_own
from hydrahive.federation import peer_identity
from hydrahive.modules import catalog_sources
from hydrahive.modules.context import ModuleContext
from tests._own_rows import only_own_rows
from tests.test_federation_catalog_e1 import _cleanup, _settings_body


@pytest.fixture(autouse=True)
def _clean(client, admin_headers):
    _cleanup(client, admin_headers)
    catalog_changes._reset_for_tests()
    with only_own_rows(
        "federation_catalog_settings", "federation_catalog_users",
        "federation_catalog_excluded_projects", "federation_catalog_deletions",
    ):
        yield
    _cleanup(client, admin_headers)
    catalog_changes._reset_for_tests()


def _active_peer(client, admin_headers, name: str = "client-x") -> dict:
    from tests.test_federation_peers import _foreign_code

    code, fp = _foreign_code(name)
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": code}).json()
    ok = client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp})
    assert ok.status_code == 200
    return ok.json()


def _accept(client, admin_headers, peer_id: str) -> None:
    r = client.put(f"/api/federation/peers/{peer_id}/catalog", headers=admin_headers, json={"accept": True})
    assert r.status_code == 200, r.text


def _settings(client, admin_headers, **over):
    r = client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(**over))
    assert r.status_code == 200, r.text


def _touch_hub(username: str = "testuser") -> None:
    ModuleContext("tasks").catalog_changed("task", username, "own-1")


# --- catalog_changes: Hub-Vormerkung getrennt vom Client-Push --------------


def test_hub_mit_shared_merkt_vor(client, admin_headers):
    peer = _active_peer(client, admin_headers)
    _accept(client, admin_headers, peer["id"])
    _settings(client, admin_headers, shared=True, users=["testuser"], enabled=False)
    assert catalog_changes.refresh_gate.__call__() is False  # Client-Push bleibt aus (enabled=False)
    assert catalog_changes.hub_gate_active() is True
    _touch_hub()
    assert catalog_changes.pending_hub_count() == 1
    assert catalog_changes.pending_count() == 0  # Client-Push unberührt


def test_hub_ohne_shared_merkt_nicht_vor(client, admin_headers):
    peer = _active_peer(client, admin_headers)
    _accept(client, admin_headers, peer["id"])
    _settings(client, admin_headers, shared=False, users=["testuser"])
    catalog_changes.refresh_gate()
    assert catalog_changes.hub_gate_active() is False
    _touch_hub()
    assert catalog_changes.pending_hub_count() == 0


def test_instanz_ohne_hub_merkt_nichts_vor_und_sendet_nichts(client, admin_headers, monkeypatch):
    """Keine angenommenen Partner (kein eigener Hub-Partner): hub_gate_active
    bleibt False, drain_hub() liefert nie etwas, hub_tick() ruft send_signed
    (bzw. hier den darunterliegenden Push) nie auf."""
    from hydrahive.federation import catalog_sync

    calls = []
    monkeypatch.setattr(catalog_sync, "send_signed", lambda *a, **kw: calls.append((a, kw)))
    _settings(client, admin_headers, shared=True, users=["testuser"])  # shared an, aber kein Partner nimmt an
    catalog_changes.refresh_gate()
    assert catalog_changes.hub_gate_active() is False
    _touch_hub()
    assert catalog_changes.pending_hub_count() == 0
    assert catalog_changes.drain_hub() == ([], False)
    assert calls == []


def test_client_push_drain_bleibt_leer_bei_reiner_hub_vormerkung(client, admin_headers):
    """Diese Instanz hat einen eigenen Partner (Hub-Vormerkung aktiv), aber
    keinen eigenen Hub gesetzt (Client-Push bleibt aus): drain() ist leer,
    obwohl drain_hub() etwas enthält."""
    peer = _active_peer(client, admin_headers)
    _accept(client, admin_headers, peer["id"])
    _settings(client, admin_headers, shared=True, users=["testuser"], enabled=False)
    catalog_changes.refresh_gate()
    _touch_hub()
    assert catalog_changes.pending_hub_count() == 1

    client_entries, client_overflow = catalog_changes.drain()
    assert client_entries == [] and client_overflow is False

    hub_entries, hub_overflow = catalog_changes.drain_hub()
    assert len(hub_entries) == 1 and hub_overflow is False


# --- catalog_hub_own.hub_distribute_step() ----------------------------------


class _FakeSource:
    def __init__(self, rows: dict) -> None:
        self.rows = rows

    def get_full(self, username, item_id):
        row = self.rows.get(item_id)
        return dict(row, owner=username) if row and row.get("owner", username) == username else None


@pytest.fixture
def fake_source(monkeypatch):
    rows: dict[str, dict] = {}
    source = _FakeSource(rows)
    snap = dict(catalog_sources.CATALOG_SOURCES)
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES["task"] = ("tasks", source)
    yield rows
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES.update(snap)


def _own_fp() -> str:
    return peer_identity.fingerprint(peer_identity.public_key_b64())


def test_geloeschter_eigener_eintrag_ergibt_loeschzeile(client, fake_source):
    catalog_changes._pending_hub.add(("task", "testuser", "gone-1"))
    # Quelle liefert nichts für "gone-1" → fehlt

    changed = hub_own.hub_distribute_step()

    assert changed is True
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_deletions WHERE origin_fp = ? AND item_id = 'gone-1'",
            (_own_fp(),),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["owner"] == "testuser" and rows[0]["kind"] == "task"
    with db() as c:
        c.execute("DELETE FROM federation_catalog_deletions WHERE item_id = 'gone-1'")


def test_vorhandener_eigener_eintrag_ergibt_keine_loeschzeile(client, fake_source):
    fake_source["there-1"] = {"project_id": None}
    catalog_changes._pending_hub.add(("task", "testuser", "there-1"))

    changed = hub_own.hub_distribute_step()

    assert changed is False
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_deletions WHERE item_id = 'there-1'",
        ).fetchall()
    assert rows == []


def test_ausgeschlossenes_projekt_ergibt_loeschzeile(client, admin_headers, fake_source):
    fake_source["excl-1"] = {"project_id": "proj-x"}
    _settings(client, admin_headers, excluded_projects=["proj-x"])
    catalog_changes._pending_hub.add(("task", "testuser", "excl-1"))

    changed = hub_own.hub_distribute_step()

    assert changed is True
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM federation_catalog_deletions WHERE item_id = 'excl-1'",
        ).fetchone()
    assert row is not None
    with db() as c:
        c.execute("DELETE FROM federation_catalog_deletions WHERE item_id = 'excl-1'")


def test_leere_vormerkung_tut_nichts(client):
    assert hub_own.hub_distribute_step() is False


def test_write_deletion_rev_steigt_wie_bei_items(client, fake_source):
    """Rev-Kontinuität: eine Löschzeile aus hub_distribute_step bekommt eine
    höhere rev als ein zuvor manuell geschriebener Eintrag."""
    with db(immediate=True) as conn:
        before = revs.next_rev(conn)
    catalog_changes._pending_hub.add(("task", "testuser", "gone-2"))

    hub_own.hub_distribute_step()

    with db() as conn:
        row = conn.execute(
            "SELECT rev FROM federation_catalog_deletions WHERE item_id = 'gone-2'",
        ).fetchone()
    assert row["rev"] > before
    with db() as c:
        c.execute("DELETE FROM federation_catalog_deletions WHERE item_id = 'gone-2'")
