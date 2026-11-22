"""K2 — Katalog auf dem Hub: Liste und Detail (docs/specs/federation-catalog.md §API, §Ablauf 4).

AK 6 (nur Metadaten gespeichert, solange niemand öffnet), AK 7 (Detail lädt live;
Ursprung aus → Snapshot bzw. Metadaten mit „zuletzt gesehen“), AK 11 (Nutzer
sieht nur seinen Namen, Admin alles), Task f3eeec36 (gelöschte Anmerkung bleibt
nicht im Snapshot). Der Ursprung wird über ``request_signed`` gefälscht.
"""
from __future__ import annotations

import httpx
import pytest

from hydrahive.federation import catalog_detail
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.peer_outbound import ReplyUnavailable
from hydrahive.modules import catalog_sources
from tests._catalog_fakes import FakeSource
from tests.test_federation_catalog_push_hub import _item, _push, _send

pytest_plugins = ["tests.test_federation_catalog_push_hub"]  # Fixture `hub` (Partner mit catalog_accept)

T0 = "2026-11-21T10:00:00Z"
T1 = "2026-11-21T10:00:01Z"


class FakeOrigin:
    """Ersetzt request_signed: liefert, was der Ursprung gerade hat."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self.mode = "online"          # online · offline · timeout · gone · forged · too_large
        self.calls: list[dict] = []

    async def __call__(self, peer, path, payload, *, reply_kind, timeout):
        assert path == "/api/peering/catalog/fetch" and reply_kind == "catalog_item" and timeout == 10.0
        self.calls.append(payload)
        if self.mode == "offline":
            raise httpx.ConnectError("aus", request=httpx.Request("POST", peer["url"]))
        if self.mode == "timeout":
            raise httpx.ReadTimeout("zu langsam", request=httpx.Request("POST", peer["url"]))
        if self.mode == "gone":
            raise ReplyUnavailable(peer["name"])
        if self.mode == "forged":
            raise proto.PeerRejected("peer_signature_invalid")
        if self.mode == "too_large":                # Antwort über MAX_REPLY_BYTES
            raise proto.PeerRejected("peer_payload_too_large")
        return {"kind": "catalog_item", "in_reply_to": payload["msg_id"], "item": dict(self.items[payload["item_id"]])}


@pytest.fixture
def remote(client, hub, monkeypatch):
    fp, peer = hub
    origin = FakeOrigin()
    monkeypatch.setattr(catalog_detail, "request_signed", origin)
    items = [_item("t-till", owner="testuser", title="Steuer"), _item("t-anna", owner="anna", title="Garten"),
             _item("i-till", kind="idea", status="new", owner="testuser", title="Steuer-Idee", updated_at=T1)]
    assert _send(client, fp, _push(1, items)).status_code == 200
    origin.items["t-till"] = {**items[0], "description": "Belege sammeln"}
    origin.items["i-till"] = {**items[2], "body": "Idee", "notes": [{"author": "agent", "body": "Notiz A"}]}
    snap = dict(catalog_sources.CATALOG_SOURCES)
    local = FakeSource("task")
    local.put("t-lokal", "2026-11-21T09:00:00Z", owner="testuser", title="Lokal")
    local.put("t-admin", "2026-11-21T09:00:00Z", owner="admin", title="Admin lokal")
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES["task"] = ("tasks", local.as_source())
    yield {"fp": fp, "peer": peer, "origin": origin}
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES.update(snap)


def _row(peer_id, item_id):
    from hydrahive.db.connection import db
    with db() as conn:
        return dict(conn.execute("SELECT * FROM federation_catalog_items WHERE peer_id = ? AND item_id = ?",
                                 (peer_id, item_id)).fetchone())


def _ids(r):
    return [i["item_id"] for i in r.json()["items"]]


# --- Liste, AK 11 ---------------------------------------------------------------

def test_ak11_nutzer_sieht_nur_eigene_admin_alles(client, remote, auth_headers, admin_headers):
    mine = client.get("/api/federation/catalog", headers=auth_headers)
    assert mine.status_code == 200
    assert _ids(mine) == ["i-till", "t-till", "t-lokal"]        # neueste zuerst, eigene lokale dabei
    assert {i["owner"] for i in mine.json()["items"]} == {"testuser"}
    every = _ids(client.get("/api/federation/catalog", headers=admin_headers))
    assert {"t-anna", "t-admin", "t-till", "t-lokal", "i-till"} <= set(every)


def test_liste_felder_und_instanzen(client, remote, auth_headers):
    body = client.get("/api/federation/catalog", headers=auth_headers).json()
    item = body["items"][0]
    assert item["instance"] == "hydrahome" and item["local"] is False and item["short_id"] == "i-till"[:8]
    assert "description" not in item and "body" not in item
    lokal = [i for i in body["items"] if i["local"]][0]
    assert lokal["peer_id"] is None and lokal["instance"] is None
    names = {i["id"]: i for i in body["instances"]}
    assert names["local"]["local"] is True and names[remote["peer"]["id"]]["stale"] is False
    assert set(names[remote["peer"]["id"]]) == {"id", "name", "local", "stale"}   # L7: Nicht-Admins knapp


def test_filter_suche_und_seiten(client, remote, auth_headers):
    get = lambda **p: _ids(client.get("/api/federation/catalog", headers=auth_headers, params=p))  # noqa: E731
    assert get(kind="idea") == ["i-till"]
    assert get(instance="local") == ["t-lokal"]
    assert get(instance=remote["peer"]["id"]) == ["i-till", "t-till"]
    assert get(q="steu") == ["i-till", "t-till"]                     # FTS-Präfix über den Titel
    assert get(status="new") == ["i-till"] and get(open_only="true", kind="task") == ["t-till", "t-lokal"]
    page = client.get("/api/federation/catalog", headers=auth_headers, params={"limit": 1, "offset": 1}).json()
    assert [i["item_id"] for i in page["items"]] == ["t-till"] and page["has_more"] is True


def test_suche_mit_sonderzeichen_kein_fehler(client, remote, auth_headers):
    r = client.get("/api/federation/catalog", headers=auth_headers, params={"q": 'a" OR "b* NEAR('})
    assert r.status_code == 200


# --- AK 6: nur Metadaten, bis jemand öffnet ----------------------------------------

def test_ak6_ohne_oeffnen_kein_volltext(client, remote):
    row = _row(remote["peer"]["id"], "t-till")
    assert row["snapshot_body"] is None and "description" not in row


# --- AK 7: Detail live und offline -------------------------------------------------

def test_ak7_detail_live_und_snapshot(client, remote, auth_headers):
    url = f"/api/federation/catalog/{remote['peer']['id']}/task/t-till"
    r = client.get(url, headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "live" and body["content"] == {"description": "Belege sammeln"}
    assert body["origin"]["online"] is True and body["item"]["title"] == "Steuer"
    assert remote["origin"].calls[0]["owner"] == "testuser"
    assert _row(remote["peer"]["id"], "t-till")["snapshot_body"]


@pytest.mark.parametrize("mode", ["offline", "timeout", "forged", "too_large"])
def test_ak7_ursprung_aus_zeigt_snapshot_mit_stand_und_zuletzt_gesehen(client, remote, auth_headers, mode):
    url = f"/api/federation/catalog/{remote['peer']['id']}/task/t-till"
    client.get(url, headers=auth_headers)                            # Snapshot entsteht
    remote["origin"].mode = mode
    body = client.get(url, headers=auth_headers).json()
    assert body["source"] == "snapshot" and body["content"] == {"description": "Belege sammeln"}
    assert body["snapshot_at"] and body["snapshot_stale"] is False
    assert body["origin"] == {"name": "hydrahome", "online": False, "last_seen": body["origin"]["last_seen"]}
    assert body["origin"]["last_seen"]


def test_ak7_ohne_snapshot_nur_metadaten_und_veraltet_hinweis(client, remote, auth_headers):
    url = f"/api/federation/catalog/{remote['peer']['id']}/task/t-till"
    remote["origin"].mode = "offline"
    body = client.get(url, headers=auth_headers).json()
    assert body["source"] == "none" and body["content"] is None and body["item"]["title"] == "Steuer"
    remote["origin"].mode = "online"
    client.get(url, headers=auth_headers)
    _send(client, remote["fp"], _push(2, [_item("t-till", owner="testuser", title="Steuer neu", updated_at=T1)]))
    remote["origin"].mode = "offline"
    body = client.get(url, headers=auth_headers).json()
    assert body["source"] == "snapshot" and body["snapshot_stale"] is True and body["item"]["title"] == "Steuer neu"


def test_ursprung_404_behaelt_snapshot(client, remote, auth_headers):
    """Review #738 M1: 404 kann auch Rate-Limit/Uhrabweichung sein → Snapshot bleibt,
    Aufräumen gelöschter Einträge macht der Abgleich."""
    url = f"/api/federation/catalog/{remote['peer']['id']}/task/t-till"
    client.get(url, headers=auth_headers)
    remote["origin"].mode = "gone"
    body = client.get(url, headers=auth_headers).json()
    assert body["source"] == "snapshot" and body["content"] == {"description": "Belege sammeln"}
    assert body["snapshot_at"] and body["origin"]["online"] is True
    assert _row(remote["peer"]["id"], "t-till")["snapshot_body"]


def test_ungueltige_metadaten_beim_nachladen_nur_snapshot(client, remote, auth_headers):
    """Review #738 L4: Metadaten aus dem Nachladen wie beim Push prüfen."""
    remote["origin"].items["t-till"].update(status="kaputt", title="x" * 400, updated_at=T1)
    body = client.get(f"/api/federation/catalog/{remote['peer']['id']}/task/t-till", headers=auth_headers).json()
    assert body["source"] == "live" and body["content"] == {"description": "Belege sammeln"}
    row = _row(remote["peer"]["id"], "t-till")
    assert row["status"] == "open" and row["title"] == "Steuer" and row["snapshot_body"]


def test_lokale_quelle_wirft_gibt_404(client, remote, auth_headers, monkeypatch):
    def boom(*a):
        raise RuntimeError("Quelle kaputt")
    src = catalog_sources.CATALOG_SOURCES["task"][1]
    monkeypatch.setitem(catalog_sources.CATALOG_SOURCES, "task", ("tasks", src.__class__(
        kind="task", list_changed=src.list_changed, list_versions=src.list_versions, get_full=boom, query=src.query)))
    assert client.get("/api/federation/catalog/local/task/t-lokal", headers=auth_headers).status_code == 404


def test_ak11_fremder_eintrag_404_admin_darf(client, remote, auth_headers, admin_headers):
    url = f"/api/federation/catalog/{remote['peer']['id']}/task/t-anna"
    remote["origin"].items["t-anna"] = {**_item("t-anna", owner="anna", title="Garten"), "description": "privat"}
    r = client.get(url, headers=auth_headers)
    assert r.status_code == 404 and remote["origin"].calls == []
    assert client.get(url, headers=admin_headers).json()["content"] == {"description": "privat"}


def test_lokaler_eintrag_direkt_aus_quelle(client, remote, auth_headers):
    body = client.get("/api/federation/catalog/local/task/t-lokal", headers=auth_headers).json()
    assert body["source"] == "live" and body["item"]["local"] is True and body["content"]["description"] == "x"
    assert client.get("/api/federation/catalog/local/task/t-admin", headers=auth_headers).status_code == 404


# --- Task f3eeec36: gelöschte Anmerkung -------------------------------------------

def test_f3eeec36_geloeschte_anmerkung_bleibt_nicht_im_snapshot(client, remote, auth_headers):
    url = f"/api/federation/catalog/{remote['peer']['id']}/idea/i-till"
    assert client.get(url, headers=auth_headers).json()["content"]["notes"][0]["body"] == "Notiz A"
    remote["origin"].items["i-till"]["notes"] = []                    # Anmerkung gelöscht, updated_at gleich
    body = client.get(url, headers=auth_headers).json()
    assert body["source"] == "live" and body["content"]["notes"] == []
    remote["origin"].mode = "offline"
    assert client.get(url, headers=auth_headers).json()["content"]["notes"] == []
