"""E2–E4/E6 — Föderations-Katalog, Routen (docs/specs/federation-catalog.md,
_work/federation-catalog/e1-api-vertrag.md). Etappe 1: nur Hub-Markierung
und Katalog-Einstellungen, noch kein Versand.
"""
from __future__ import annotations

import pytest

from tests._own_rows import only_own_rows
from tests.conftest import error_code, error_params
from tests.test_federation_peers import _foreign_code


def _add_active_peer(client, admin_headers, name: str = "vps") -> dict:
    code, fp = _foreign_code(name)
    r = client.post("/api/federation/peers", headers=admin_headers, json={"code": code})
    assert r.status_code == 201, r.text
    peer = r.json()
    ok = client.post(
        f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers,
        json={"fingerprint": fp},
    )
    assert ok.status_code == 200, ok.text
    return ok.json()


# Katalog-Tabellen: nur Zeilen löschen, die im Test dazugekommen sind (kein DELETE
# ohne WHERE, test_no_broad_deletes). Sonst hängt z. B. test_get_settings_defaults
# davon ab, welcher Test vorher Einstellungen gespeichert hat.
CATALOG_TABLES = (
    "federation_catalog_settings", "federation_catalog_users",
    "federation_catalog_excluded_projects", "federation_catalog_cursors",
)


def _cleanup(client, admin_headers):
    for p in client.get("/api/federation/peers", headers=admin_headers).json():
        client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)


@pytest.fixture(autouse=True)
def _clean(client, admin_headers):
    _cleanup(client, admin_headers)
    with only_own_rows(*CATALOG_TABLES):
        yield
    _cleanup(client, admin_headers)


# --- GET /api/federation/peers liefert is_hub/catalog_accept als bool ------

def test_list_peers_exposes_is_hub_and_catalog_accept_as_bool(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    assert peer["is_hub"] is False
    assert peer["catalog_accept"] is False
    listed = client.get("/api/federation/peers", headers=admin_headers).json()
    assert listed[0]["is_hub"] is False
    assert listed[0]["catalog_accept"] is False


# --- E2: PUT /api/federation/peers/{id}/hub ---------------------------------

def test_set_hub_requires_admin(client, auth_headers, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    r = client.put(
        f"/api/federation/peers/{peer['id']}/hub", headers=auth_headers, json={"is_hub": True},
    )
    assert r.status_code == 403


def test_set_hub_unknown_peer_404(client, admin_headers):
    r = client.put(
        "/api/federation/peers/does-not-exist/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert r.status_code == 404
    assert error_code(r) == "peer_not_found"


def test_set_hub_rejects_inactive_peer(client, admin_headers):
    code, fp = _foreign_code("pending-peer")
    r = client.post("/api/federation/peers", headers=admin_headers, json={"code": code})
    pending = r.json()
    assert pending["status"] == "pending"

    hub = client.put(
        f"/api/federation/peers/{pending['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert hub.status_code == 409
    assert error_code(hub) == "peer_not_active"


def test_set_hub_blocked_peer_rejected(client, admin_headers):
    peer = _add_active_peer(client, admin_headers, "blocked-peer")
    client.post(f"/api/federation/peers/{peer['id']}/block", headers=admin_headers)

    hub = client.put(
        f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert hub.status_code == 409
    assert error_code(hub) == "peer_not_active"


def test_set_hub_true_then_false_and_only_one_hub(client, admin_headers):
    first = _add_active_peer(client, admin_headers, "hub-a")
    second = _add_active_peer(client, admin_headers, "hub-b")

    ok = client.put(
        f"/api/federation/peers/{first['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["is_hub"] is True

    conflict = client.put(
        f"/api/federation/peers/{second['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert conflict.status_code == 409
    assert error_code(conflict) == "catalog_hub_exists"
    assert error_params(conflict)["name"] == "hub-a"

    off = client.put(
        f"/api/federation/peers/{first['id']}/hub", headers=admin_headers, json={"is_hub": False},
    )
    assert off.status_code == 200
    assert off.json()["is_hub"] is False

    now_ok = client.put(
        f"/api/federation/peers/{second['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert now_ok.status_code == 200


# --- E3: Hub <-> Annehmen gegenseitiger Ausschluss --------------------------

def test_hub_conflicts_with_accepting_from_another_peer(client, admin_headers):
    accepted_from = _add_active_peer(client, admin_headers, "upstream")
    candidate_hub = _add_active_peer(client, admin_headers, "downstream")

    accept = client.put(
        f"/api/federation/peers/{accepted_from['id']}/catalog",
        headers=admin_headers, json={"accept": True},
    )
    assert accept.status_code == 200, accept.text

    hub = client.put(
        f"/api/federation/peers/{candidate_hub['id']}/hub",
        headers=admin_headers, json={"is_hub": True},
    )
    assert hub.status_code == 409
    assert error_code(hub) == "catalog_hub_conflict"


def test_accept_conflicts_with_hub_set(client, admin_headers):
    hub_peer = _add_active_peer(client, admin_headers, "hub-peer")
    other_peer = _add_active_peer(client, admin_headers, "other-peer")

    hub = client.put(
        f"/api/federation/peers/{hub_peer['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert hub.status_code == 200

    accept = client.put(
        f"/api/federation/peers/{other_peer['id']}/catalog",
        headers=admin_headers, json={"accept": True},
    )
    assert accept.status_code == 409
    assert error_code(accept) == "catalog_hub_conflict"


def test_set_catalog_accept_unknown_peer_404(client, admin_headers):
    r = client.put(
        "/api/federation/peers/does-not-exist/catalog", headers=admin_headers, json={"accept": True},
    )
    assert r.status_code == 404
    assert error_code(r) == "peer_not_found"


def test_set_catalog_accept_requires_admin(client, auth_headers, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    r = client.put(
        f"/api/federation/peers/{peer['id']}/catalog", headers=auth_headers, json={"accept": True},
    )
    assert r.status_code == 403


def test_set_catalog_accept_rejects_inactive_peer(client, admin_headers):
    code, fp = _foreign_code("pending-accept")
    r = client.post("/api/federation/peers", headers=admin_headers, json={"code": code})
    pending = r.json()

    accept = client.put(
        f"/api/federation/peers/{pending['id']}/catalog",
        headers=admin_headers, json={"accept": True},
    )
    assert accept.status_code == 409
    assert error_code(accept) == "peer_not_active"


def test_set_catalog_accept_false_always_allowed(client, admin_headers):
    peer = _add_active_peer(client, admin_headers)
    off = client.put(
        f"/api/federation/peers/{peer['id']}/catalog", headers=admin_headers, json={"accept": False},
    )
    assert off.status_code == 200
    assert off.json()["catalog_accept"] is False


# --- E4: GET/PUT /api/federation/catalog/settings ---------------------------

def test_get_settings_defaults(client, admin_headers):
    r = client.get("/api/federation/catalog/settings", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["interval_seconds"] == 300
    assert body["users"] == []
    assert body["excluded_projects"] == []
    assert body["hub"] is None
    assert body["accepting_from"] == []
    assert body["last_push_at"] is None
    assert body["last_ok_at"] is None
    assert body["last_full_at"] is None
    assert body["last_error"] is None


def test_get_settings_requires_admin(client, auth_headers):
    r = client.get("/api/federation/catalog/settings", headers=auth_headers)
    assert r.status_code == 403


def _settings_body(**over):
    base = {
        "enabled": True,
        "interval_seconds": 120,
        "users": ["testuser"],
        "excluded_projects": ["proj-a"],
    }
    base.update(over)
    return base


def test_put_settings_valid(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["interval_seconds"] == 120
    assert body["users"] == ["testuser"]
    assert body["excluded_projects"] == ["proj-a"]

    again = client.get("/api/federation/catalog/settings", headers=admin_headers)
    assert again.json() == body


@pytest.mark.parametrize("interval", [59, 3601])
def test_put_settings_rejects_interval_out_of_range(client, admin_headers, interval):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(interval_seconds=interval),
    )
    assert r.status_code == 422


def test_put_settings_rejects_non_int_interval(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(interval_seconds="300s"),
    )
    assert r.status_code == 422


def test_put_settings_unknown_user_400(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["gibt-es-nicht"]),
    )
    assert r.status_code == 400
    assert error_code(r) == "catalog_user_unknown"
    assert error_params(r)["username"] == "gibt-es-nicht"


def test_put_settings_removes_duplicates(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["testuser", "testuser"], excluded_projects=["proj-a", "proj-a"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["users"] == ["testuser"]
    assert body["excluded_projects"] == ["proj-a"]


def test_put_settings_enabled_without_hub_allowed(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=[], excluded_projects=[]),
    )
    assert r.status_code == 200
    assert r.json()["hub"] is None
    assert r.json()["enabled"] is True


def test_put_settings_requires_admin(client, auth_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=auth_headers, json=_settings_body(),
    )
    assert r.status_code == 403


def test_get_settings_shows_hub_and_accepting_from(client, admin_headers):
    hub_peer = _add_active_peer(client, admin_headers, "hub-x")
    client.put(f"/api/federation/peers/{hub_peer['id']}/hub", headers=admin_headers, json={"is_hub": True})

    r = client.get("/api/federation/catalog/settings", headers=admin_headers)
    body = r.json()
    assert body["hub"] == {"id": hub_peer["id"], "name": "hub-x", "status": "active"}

    client.put(f"/api/federation/peers/{hub_peer['id']}/hub", headers=admin_headers, json={"is_hub": False})
    accepting_peer = _add_active_peer(client, admin_headers, "accepting-y")
    client.put(
        f"/api/federation/peers/{accepting_peer['id']}/catalog",
        headers=admin_headers, json={"accept": True},
    )
    r2 = client.get("/api/federation/catalog/settings", headers=admin_headers)
    assert r2.json()["accepting_from"] == [{"id": accepting_peer["id"], "name": "accepting-y"}]


# --- Cursor-Reset bei Auswahländerung und Hub-Wechsel -----------------------

def test_cursor_reset_on_user_selection_change(client, admin_headers):
    from hydrahive.db import federation_catalog as catalog_db
    from hydrahive.db.connection import db

    client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["testuser"], excluded_projects=[]),
    )
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_catalog_cursors (username, kind, cursor_updated_at) "
            "VALUES ('testuser', 'task', '2026-01-01T00:00:00Z')",
        )
    assert catalog_db.list_selected_users() == ["testuser"]

    # Auswahl unverändert -> Cursor bleibt stehen.
    client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["testuser"], excluded_projects=[]),
    )
    with db() as conn:
        remaining = conn.execute("SELECT * FROM federation_catalog_cursors").fetchall()
    assert len(remaining) == 1

    # Auswahl geändert -> Cursor wird geleert.
    client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["testuser", "admin"], excluded_projects=[]),
    )
    with db() as conn:
        remaining2 = conn.execute("SELECT * FROM federation_catalog_cursors").fetchall()
    assert remaining2 == []


def test_cursor_reset_on_hub_change(client, admin_headers):
    from hydrahive.db.connection import db

    peer = _add_active_peer(client, admin_headers, "hub-cursor")
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_catalog_cursors (username, kind, cursor_updated_at) "
            "VALUES ('testuser', 'idea', '2026-01-01T00:00:00Z')",
        )
    client.put(f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": True})
    with db() as conn:
        remaining = conn.execute("SELECT * FROM federation_catalog_cursors").fetchall()
    assert remaining == []


# --- E6: kein Netzverkehr ---------------------------------------------------

def test_no_network_traffic_in_catalog_routes(client, admin_headers, monkeypatch):
    """Alle neuen Routen durchlaufen lassen, während send_signed/httpx beim
    Aufruf fehlschlagen — bricht keiner davon aus, gab es keinen Netzversand.
    """
    import httpx

    from hydrahive.federation import peer_inbound, peer_outbound

    def _boom(*args, **kwargs):
        raise AssertionError("E6: kein Netzverkehr in Etappe 1 erlaubt")

    async def _async_boom(*args, **kwargs):
        raise AssertionError("E6: kein Netzverkehr in Etappe 1 erlaubt")

    monkeypatch.setattr(peer_inbound, "send_signed", _async_boom)
    monkeypatch.setattr(peer_outbound, "send_signed", _async_boom)
    monkeypatch.setattr(httpx.AsyncClient, "post", _boom)
    monkeypatch.setattr(httpx.AsyncClient, "request", _boom)

    peer = _add_active_peer(client, admin_headers, "no-network-peer")

    r1 = client.put(
        f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": True},
    )
    assert r1.status_code == 200, r1.text

    r2 = client.put(
        f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": False},
    )
    assert r2.status_code == 200, r2.text

    r3 = client.put(
        f"/api/federation/peers/{peer['id']}/catalog", headers=admin_headers, json={"accept": True},
    )
    assert r3.status_code == 200, r3.text

    r4 = client.get("/api/federation/catalog/settings", headers=admin_headers)
    assert r4.status_code == 200

    r5 = client.put(
        "/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(),
    )
    assert r5.status_code == 200, r5.text
