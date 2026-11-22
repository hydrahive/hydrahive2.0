"""Auftrag B3, Stück 3 — Ausschluss beim Hub (docs/specs/federation-shared-
tasks.md §Schalter "Der Hub schließt bei sich etwas aus"): Nutzer abgewählt
oder Projekt neu ausgeschlossen schreibt Löschzeilen für die betroffenen
EIGENEN Einträge; Gegenrichtung setzt reset_local = 1.
"""
from __future__ import annotations

import pytest

from hydrahive.db.connection import db
from hydrahive.federation import catalog_changes
from hydrahive.federation import peer_identity
from hydrahive.modules import catalog_sources
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


class _FakeSource:
    def __init__(self, rows: dict) -> None:
        self.rows = rows  # username -> list[(item_id, updated_at, project_id)]

    def list_versions(self, username):
        return list(self.rows.get(username, []))

    def get_full(self, username, item_id):
        for iid, updated_at, project_id in self.rows.get(username, []):
            if iid == item_id:
                return {"project_id": project_id, "updated_at": updated_at, "owner": username}
        return None


@pytest.fixture
def fake_source():
    rows: dict[str, list] = {}
    source = _FakeSource(rows)
    snap = dict(catalog_sources.CATALOG_SOURCES)
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES["task"] = ("tasks", source)
    yield rows
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES.update(snap)


def _own_fp() -> str:
    return peer_identity.fingerprint(peer_identity.public_key_b64())


def _deletions() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_catalog_deletions WHERE origin_fp = ?", (_own_fp(),),
        ).fetchall()
    return [dict(r) for r in rows]


def _settings_put(client, admin_headers, **over):
    r = client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(**over))
    assert r.status_code == 200, r.text
    return r


def _reset_local_flags() -> list[int]:
    with db() as conn:
        rows = conn.execute("SELECT reset_local FROM federation_catalog_sources").fetchall()
    return [r["reset_local"] for r in rows]


def _make_peer_source(client, admin_headers):
    """Eine Zeile in federation_catalog_sources anlegen (für reset_local-Test)."""
    from tests.test_federation_peers import _foreign_code

    code, fp = _foreign_code("src-peer")
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": code}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp})
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_catalog_sources (peer_id, last_seq, reset_local) VALUES (?, 0, 0)",
            (peer["id"],),
        )
    return peer


def test_nutzer_abgewaehlt_schreibt_loeschzeilen_fuer_eigene_eintraege(client, admin_headers, fake_source):
    fake_source["admin"] = [("t1", "2026-11-22T00:00:00Z", None), ("t2", "2026-11-22T00:00:00Z", None)]
    _settings_put(client, admin_headers, users=["admin", "testuser"], excluded_projects=[])

    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])  # admin abgewählt

    dels = _deletions()
    assert {d["item_id"] for d in dels} == {"t1", "t2"}
    assert all(d["owner"] == "admin" for d in dels)


def test_nutzer_bleibt_ausgewaehlt_keine_loeschzeilen(client, admin_headers, fake_source):
    fake_source["testuser"] = [("t1", "2026-11-22T00:00:00Z", None)]
    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])

    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])  # unverändert

    assert _deletions() == []


def test_projekt_neu_ausgeschlossen_schreibt_loeschzeilen(client, admin_headers, fake_source):
    fake_source["testuser"] = [
        ("t1", "2026-11-22T00:00:00Z", "proj-a"),
        ("t2", "2026-11-22T00:00:00Z", "proj-b"),
    ]
    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])

    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=["proj-a"])

    dels = _deletions()
    assert {d["item_id"] for d in dels} == {"t1"}  # nur proj-a betroffen


def test_nutzer_wieder_ausgewaehlt_setzt_reset_local(client, admin_headers, fake_source):
    peer = _make_peer_source(client, admin_headers)
    _settings_put(client, admin_headers, users=[], excluded_projects=[])

    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])  # wieder ausgewählt

    assert _reset_local_flags() == [1]
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer["id"],))


def test_projekt_wieder_freigegeben_setzt_reset_local(client, admin_headers, fake_source):
    peer = _make_peer_source(client, admin_headers)
    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=["proj-a"])

    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])  # proj-a wieder frei

    assert _reset_local_flags() == [1]
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer["id"],))


def test_unveraendert_setzt_kein_reset_local(client, admin_headers, fake_source):
    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])
    peer = _make_peer_source(client, admin_headers)  # erst NACH dem ersten (ändernden) Put anlegen

    _settings_put(client, admin_headers, users=["testuser"], excluded_projects=[])  # keine Änderung

    assert _reset_local_flags() == [0]
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer["id"],))
