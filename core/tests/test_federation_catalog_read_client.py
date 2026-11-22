"""G3/P2 — ctx.catalog_foreign_get auf dem Client (AK G14): Volltext über den Hub
(catalog_read), Ursprung offline → Snapshot, Hub offline → Metadaten aus der Kopie,
kein Volltext gespeichert, Größengrenze und Signatur wie request_signed.

Dieselbe Test-DB spielt Hub und Client (Muster tests/_catalog_pull_client_env.py): Die
Anfrage geht an die echte Hub-Route, signiert mit dem Schlüssel von C.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from hydrahive.db.connection import db
from hydrahive.federation import catalog_detail, catalog_pull_client as pc, catalog_read_client as rc
from hydrahive.federation import catalog_read_hub, peer_protocol as proto
from hydrahive.federation.peer_outbound import ReplyUnavailable
from hydrahive.modules.context import ModuleContext
from tests._catalog_pull_env import item, push

pytest_plugins = ["tests._catalog_pull_env", "tests._catalog_pull_client_env"]
CTX = ModuleContext("tasks")


@pytest.fixture
def read_env(client, cs, monkeypatch):
    catalog_read_hub._reset_for_tests()
    state = {"origin": "online", "hub": "online", "tamper": False}

    async def origin_fake(peer, path, payload, *, reply_kind, timeout):
        if state["origin"] == "offline":
            raise httpx.ConnectError("aus", request=httpx.Request("POST", peer["url"]))
        it = {**item(payload["item_id"]), "description": "Volltext"}
        return {"kind": "catalog_item", "in_reply_to": payload["msg_id"], "item": it}

    async def hub_fake(peer, path, payload, *, reply_kind, timeout):
        assert path == "/api/peering/catalog/read" and peer["id"] == "hub-self-test" and "seq" not in payload
        if state["hub"] == "offline":
            raise httpx.ConnectError("Hub weg", request=httpx.Request("POST", peer["url"]))
        if state["hub"] == "too_large":
            raise proto.PeerRejected("peer_payload_too_large")
        r = await asyncio.to_thread(client.post, path, json=payload, headers=cs["c"].headers(payload))
        if r.status_code == 404:
            raise ReplyUnavailable(peer["name"])
        body = r.json()
        if state["tamper"]:
            body["content"] = {"description": "untergeschoben"}
        return proto.verify_reply(peer, r.headers.get(proto.HEADER_SIGNATURE, ""), body, reply_kind,
                                  payload["msg_id"])
    monkeypatch.setattr(catalog_detail, "request_signed", origin_fake)
    monkeypatch.setattr(rc, "request_signed", hub_fake)
    push(client, cs["o"], [item("o-1")])
    yield state
    catalog_read_hub._reset_for_tests()


async def _pull_ok():
    assert await pc.pull(full=False) == "ok"


async def test_ursprung_online_volltext_ohne_speichern(read_env, cs):
    await _pull_ok()
    full = await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1")
    assert full["content"] == {"description": "Volltext"} and full["source"] == "live"
    assert full["origin_offline"] is False and full["hub_unreachable"] is False
    assert full["item"]["origin_name"] == "devbox" and full["item"]["foreign"] is True
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(federation_catalog_mirror)")}
        row = dict(conn.execute("SELECT * FROM federation_catalog_mirror WHERE item_id = 'o-1'").fetchone())
    assert not ({"description", "body", "snapshot_body"} & cols) and "Volltext" not in str(row)   # nichts gespeichert


async def test_ursprung_offline_snapshot_vom_hub(read_env, cs):
    await _pull_ok()
    await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1")          # Hub legt Snapshot an
    read_env["origin"] = "offline"
    full = await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1")
    assert full["origin_offline"] is True and full["source"] == "snapshot"
    assert full["content"] == {"description": "Volltext"} and full["snapshot_at"]


async def test_hub_offline_metadaten_aus_der_kopie(read_env, cs):
    await _pull_ok()
    read_env["hub"] = "offline"
    full = await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1")
    assert full["hub_unreachable"] is True and full["source"] == "metadata" and full["content"] is None
    assert full["item"]["title"] == "Titel o-1"


async def test_zu_grosse_oder_manipulierte_antwort(read_env, cs):
    await _pull_ok()
    read_env["hub"] = "too_large"
    assert (await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1"))["hub_unreachable"] is True
    read_env["hub"], read_env["tamper"] = "online", True
    assert (await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1"))["hub_unreachable"] is True


async def test_nicht_sichtbar_ergibt_none(read_env, cs):
    await _pull_ok()
    assert await CTX.catalog_foreign_get("task", "anna", cs["o"].fp, "o-1") is None      # fremder Nutzer
    assert await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "fehlt") is None
    with db() as conn:
        conn.execute("UPDATE federation_catalog_sources SET pull_users = '[]' WHERE peer_id = ?", (cs["c_peer"]["id"],))
    assert await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1") is None   # Hub sagt 404


async def test_ohne_gemeinsame_taskpflege_none(read_env, cs):
    await _pull_ok()
    with db() as conn:
        conn.execute("UPDATE federation_catalog_settings SET shared = 0 WHERE id = 1")
    assert await CTX.catalog_foreign_get("task", "testuser", cs["o"].fp, "o-1") is None
