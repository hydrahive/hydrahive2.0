"""G2/V4 — Kopie auf dem Client lesen: GET /api/federation/catalog/mirror (nur lesen,
eigener Nutzername, Admin alles, Filter, Suche, Facetten) und Status in den Einstellungen.
"""
from __future__ import annotations

import pytest

from hydrahive.db import federation_catalog_mirror as mirror_db

URL = "/api/federation/catalog/mirror"


def _row(item_id, *, fp="fp-a", name="hydrahome", owner="testuser", kind="task", status="open",
         project="Hydrahive DEV", updated="2026-11-22T10:00:00Z", title=None):
    return {"origin_fp": fp, "origin_name": name, "kind": kind, "item_id": item_id, "owner": owner,
            "title": title or f"Titel {item_id}", "status": status, "priority": None, "project_id": "p",
            "project_name": project, "created_at": updated, "updated_at": updated}


@pytest.fixture
def mirror():
    mirror_db.clear()
    rows = [
        _row("t-aaaaaaaa1", updated="2026-11-22T10:00:01Z"),
        _row("t-bbbbbbbb2", status="done", title="Steuer abgeben"),
        _row("i-cccccccc3", kind="idea", status="new", fp="fp-b", name="devbox", project="Garten"),
        _row("t-dddddddd4", owner="anna"),
    ]
    rev, local = mirror_db.state()
    mirror_db.apply_page(rows, [], rev, local, "2026-11-22T10:05:00Z")
    yield
    mirror_db.clear()


def test_nutzer_sieht_nur_eigene(client, auth_headers, mirror):
    r = client.get(URL, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert sorted(i["item_id"] for i in body["items"]) == ["i-cccccccc3", "t-aaaaaaaa1", "t-bbbbbbbb2"]
    assert body["items"][0]["item_id"] == "t-aaaaaaaa1"                  # neueste zuerst
    assert body["items"][0]["short_id"] == "t-aaaaaa" and body["items"][0]["origin_name"] == "hydrahome"
    assert {i["origin_name"] for i in body["facets"]["instances"]} == {"hydrahome", "devbox"}
    assert body["facets"]["projects"] == ["Garten", "Hydrahive DEV"]


def test_admin_sieht_alles(client, admin_headers, mirror):
    assert len(client.get(URL, headers=admin_headers).json()["items"]) == 4


def test_filter_und_suche(client, auth_headers, mirror):
    def ids(**params):
        return sorted(i["item_id"] for i in client.get(URL, headers=auth_headers, params=params).json()["items"])
    assert ids(kind="idea") == ["i-cccccccc3"]
    assert ids(instance="fp-b") == ["i-cccccccc3"]
    assert ids(project="Hydrahive DEV") == ["t-aaaaaaaa1", "t-bbbbbbbb2"]
    assert ids(status="done") == ["t-bbbbbbbb2"]
    assert ids(q="steuer") == ["t-bbbbbbbb2"]
    assert ids(q="t-aaa") == ["t-aaaaaaaa1"]                             # Kurz-ID
    assert ids(q="100%_") == []                                          # Platzhalter maskiert


def test_seitenweise(client, admin_headers, mirror):
    first = client.get(URL, headers=admin_headers, params={"limit": 3}).json()
    rest = client.get(URL, headers=admin_headers, params={"limit": 3, "offset": 3}).json()
    assert first["has_more"] is True and len(first["items"]) == 3
    assert rest["has_more"] is False and len(rest["items"]) == 1


def test_nur_angemeldet_und_ungueltige_werte(client, auth_headers, mirror):
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers=auth_headers, params={"kind": "ticket"}).status_code == 422
    assert client.get(URL, headers=auth_headers, params={"limit": 999}).status_code == 422


def test_route_schluckt_nicht_die_detailansicht(client, auth_headers, mirror):
    r = client.get("/api/federation/catalog/mirror/task/x", headers=auth_headers)
    assert r.status_code == 404                                          # Detail-Route, nicht /mirror


def test_status_in_den_einstellungen(client, admin_headers, mirror):
    mirror_db.record_pull_status(ok_at="2026-11-22T10:05:00Z")
    mirror_db.record_pull_status(error="peer_catalog_not_shared")
    body = client.get("/api/federation/catalog/settings", headers=admin_headers).json()
    assert body["mirror_count"] == 4
    assert body["last_pull_at"] == "2026-11-22T10:05:00Z"
    assert body["last_pull_error"] == "peer_catalog_not_shared"
    assert "last_full_pull_at" in body and "shared" in body and "remote_edits" in body
