"""Fixture ``env`` für die Tests des Katalog-Clients (S4).

Eingebunden per ``pytest_plugins = ["tests._catalog_sync_env"]``. Richtet einen
aktiven Hub-Partner, Sync-Einstellungen (Nutzer ``testuser``, Projekt
``proj-geheim`` ausgeschlossen) und zwei Quellen im Speicher ein; ``send_signed``
geht an einen gefälschten Hub mit der echten Hub-Annahme dahinter, Pausen
zwischen Nachrichten werden nur aufgezeichnet.
"""
from __future__ import annotations

import pytest

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.federation import catalog_sync
from hydrahive.modules import catalog_sources
from tests._catalog_fakes import FakeHub, FakeSource
from tests._own_rows import only_own_rows
from tests.test_federation_catalog_e1 import CATALOG_TABLES, _add_active_peer, _cleanup, _settings_body

T0 = "2026-11-21T10:00:00Z"
T1 = "2026-11-21T10:00:01Z"
I0 = "2026-11-21T10:00:00.500000Z"


@pytest.fixture
def env(client, admin_headers, monkeypatch):
    _cleanup(client, admin_headers)
    with only_own_rows(*CATALOG_TABLES, "errors_log"):
        peer = _add_active_peer(client, admin_headers, "hydrahive-vps")
        assert client.put(f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers,
                          json={"is_hub": True}).status_code == 200
        assert client.put("/api/federation/catalog/settings", headers=admin_headers,
                          json=_settings_body(excluded_projects=["proj-geheim"])).status_code == 200
        client_db.reset_cursors([("testuser", "task"), ("testuser", "idea")])
        tasks, ideas = FakeSource("task"), FakeSource("idea")
        snap = dict(catalog_sources.CATALOG_SOURCES)
        catalog_sources.CATALOG_SOURCES.clear()
        catalog_sources.CATALOG_SOURCES.update({"task": ("tasks", tasks.as_source()),
                                                "idea": ("scratchpad", ideas.as_source())})
        hub = FakeHub(peer)
        pauses: list[float] = []

        async def no_pause(seconds):
            pauses.append(seconds)
        monkeypatch.setattr(catalog_sync, "send_signed", hub)
        monkeypatch.setattr(catalog_sync, "_pause", no_pause)
        yield {"peer": peer, "hub": hub, "tasks": tasks, "ideas": ideas, "pauses": pauses}
        catalog_sources.CATALOG_SOURCES.clear()
        catalog_sources.CATALOG_SOURCES.update(snap)
        _cleanup(client, admin_headers)
