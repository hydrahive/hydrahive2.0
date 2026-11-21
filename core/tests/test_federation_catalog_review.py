"""Föderations-Katalog Etappe 1 — Nachbesserungen aus dem Review von PR #734
(docs/specs/federation-catalog.md): atomare Hub-/Annahme-Regeln in der DB-Schicht,
Cursor nur bei echter Hub-Änderung leeren, Nutzernamen ohne Zeichen-Muster.
"""
from __future__ import annotations

import pytest

from tests.conftest import error_code
from tests._own_rows import only_own_rows
from tests.test_federation_catalog_e1 import CATALOG_TABLES, _add_active_peer, _cleanup, _settings_body


@pytest.fixture(autouse=True)
def _clean(client, admin_headers):
    _cleanup(client, admin_headers)
    with only_own_rows(*CATALOG_TABLES):
        yield
    _cleanup(client, admin_headers)


def _insert_cursor():
    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO federation_catalog_cursors (username, kind, cursor_updated_at) "
            "VALUES ('testuser', 'task', '2026-01-01T00:00:00Z')",
        )


def _cursor_count() -> int:
    from hydrahive.db.connection import db

    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM federation_catalog_cursors").fetchone()[0]


def test_db_set_hub_rejects_second_hub_itself(client, admin_headers):
    """Die Regel sitzt in der Transaktion, nicht nur in der Route (kein Wettlauf → 500)."""
    from hydrahive.db import federation_catalog as catalog_db

    a = _add_active_peer(client, admin_headers, "hub-a")
    b = _add_active_peer(client, admin_headers, "hub-b")
    catalog_db.set_hub(a["id"], True)
    with pytest.raises(catalog_db.CatalogConflict) as exc:
        catalog_db.set_hub(b["id"], True)
    assert exc.value.code == "catalog_hub_exists"
    assert exc.value.params == {"name": "hub-a"}
    assert catalog_db.any_hub()["id"] == a["id"]


def test_db_accept_and_hub_exclusive_in_db_layer(client, admin_headers):
    from hydrahive.db import federation_catalog as catalog_db

    a = _add_active_peer(client, admin_headers, "x-a")
    b = _add_active_peer(client, admin_headers, "x-b")
    catalog_db.set_catalog_accept(a["id"], True)
    with pytest.raises(catalog_db.CatalogConflict) as exc:
        catalog_db.set_hub(b["id"], True)
    assert exc.value.code == "catalog_hub_conflict"
    catalog_db.set_catalog_accept(a["id"], False)
    catalog_db.set_hub(b["id"], True)
    with pytest.raises(catalog_db.CatalogConflict):
        catalog_db.set_catalog_accept(a["id"], True)


def test_db_unknown_peer_returns_none(client, admin_headers):
    from hydrahive.db import federation_catalog as catalog_db

    assert catalog_db.set_hub("gibt-es-nicht", True) is None
    assert catalog_db.set_catalog_accept("gibt-es-nicht", True) is None


def test_hub_switch_via_api_after_turning_old_off(client, admin_headers):
    """So wechselt die Oberfläche nach Rückfrage (Spec §Ablauf 1.2): alt aus, neu an."""
    a = _add_active_peer(client, admin_headers, "alt")
    b = _add_active_peer(client, admin_headers, "neu")
    assert client.put(f"/api/federation/peers/{a['id']}/hub", headers=admin_headers, json={"is_hub": True}).status_code == 200
    blocked = client.put(f"/api/federation/peers/{b['id']}/hub", headers=admin_headers, json={"is_hub": True})
    assert blocked.status_code == 409 and error_code(blocked) == "catalog_hub_exists"
    assert client.put(f"/api/federation/peers/{a['id']}/hub", headers=admin_headers, json={"is_hub": False}).status_code == 200
    ok = client.put(f"/api/federation/peers/{b['id']}/hub", headers=admin_headers, json={"is_hub": True})
    assert ok.status_code == 200 and ok.json()["is_hub"] is True


def test_cursor_kept_when_hub_flag_unchanged(client, admin_headers):
    peer = _add_active_peer(client, admin_headers, "kein-hub")
    _insert_cursor()
    # Partner ist kein Hub; "ausschalten" ändert nichts → Cursor bleibt.
    r = client.put(f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": False})
    assert r.status_code == 200
    assert _cursor_count() == 1
    # Echte Änderung → voller Abgleich.
    client.put(f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": True})
    assert _cursor_count() == 0
    _insert_cursor()
    client.put(f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": True})
    assert _cursor_count() == 1


def test_settings_accept_username_with_umlaut_and_space(client, admin_headers, monkeypatch):
    """Nutzernamen sind bei der Anlage frei; maßgeblich ist nur, dass es den Nutzer gibt."""
    from hydrahive.api.routes import federation_catalog as route

    monkeypatch.setattr(route, "list_users", lambda: [{"username": "Jörg M"}, {"username": "testuser"}])
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["Jörg M"], excluded_projects=[]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["users"] == ["Jörg M"]


def test_settings_reject_overlong_username(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(users=["x" * 129], excluded_projects=[]),
    )
    assert r.status_code == 422
