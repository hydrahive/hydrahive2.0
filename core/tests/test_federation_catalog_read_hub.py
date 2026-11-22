"""G3/P2 — Hub-Route POST /api/peering/catalog/read (federation-shared-tasks.md §catalog_read):
Verteilregel, owner in pull_users, nach außen immer 404, Replay, Ursprung online/offline,
eigene Einträge des Hubs, signierte Antwort mit in_reply_to.
"""
from __future__ import annotations

import time
import uuid

import httpx
import pytest

from hydrahive.federation import catalog_detail, catalog_read_hub, peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from tests._catalog_pull_env import item, pull, push, settings

pytest_plugins = ["tests._catalog_pull_env"]
URL = "/api/peering/catalog/read"


@pytest.fixture
def origin(monkeypatch, env):
    """Ersetzt den Ursprung O: liefert Volltext (online) oder ist offline."""
    catalog_read_hub._reset_for_tests()
    state = {"mode": "online", "calls": []}

    async def fake(peer, path, payload, *, reply_kind, timeout):
        state["calls"].append((path, timeout))
        if state["mode"] == "offline":
            raise httpx.ConnectError("aus", request=httpx.Request("POST", peer["url"]))
        it = {**item(payload["item_id"]), "description": f"Volltext {payload['item_id']}"}
        return {"kind": "catalog_item", "in_reply_to": payload["msg_id"], "item": it}
    monkeypatch.setattr(catalog_detail, "request_signed", fake)
    yield state
    catalog_read_hub._reset_for_tests()


def _read(client, fp, origin_fp, item_id="o-1", **over):
    p = proto.new_catalog_read(origin_fp, "task", item_id, "testuser")
    p.update(over)
    return client.post(URL, json=p, headers=fp.headers(p)), p


def _ready(client, env):
    push(client, env["o"], [item("o-1")])
    assert pull(client, env["c"])[0].status_code == 200          # pull_users von C = [testuser]


def test_ursprung_online_liefert_volltext_signiert(client, env, origin):
    _ready(client, env)
    r, p = _read(client, env["c"], env["o"].fp)
    assert r.status_code == 200
    body = proto.verify_reply({"name": "hub", "public_key": ident.public_key_b64()},
                              r.headers[proto.HEADER_SIGNATURE], r.json(), "catalog_item", p["msg_id"])
    assert body["content"] == {"description": "Volltext o-1"} and body["source"] == "live"
    assert body["origin_offline"] is False and body["item"]["origin_fp"] == env["o"].fp
    assert origin["calls"] == [("/api/peering/catalog/fetch", 8.0)]  # Timeout 8 s


def test_ursprung_offline_liefert_snapshot(client, env, origin):
    _ready(client, env)
    _read(client, env["c"], env["o"].fp)                        # Snapshot entsteht
    origin["mode"] = "offline"
    body = _read(client, env["c"], env["o"].fp)[0].json()
    assert body["origin_offline"] is True and body["source"] == "snapshot"
    assert body["content"] == {"description": "Volltext o-1"} and body["snapshot_at"]


def test_eigener_eintrag_des_hubs(client, env, origin):
    env["src"]["task"].put("h-1", "2026-11-22T09:00:00Z")
    env["src"]["task"].rows[("testuser", "h-1")]["description"] = "Hub-Text"
    assert pull(client, env["c"])[0].status_code == 200
    body = _read(client, env["c"], ident.fingerprint(ident.public_key_b64()), "h-1")[0].json()
    assert body["content"] == {"description": "Hub-Text"} and body["origin_offline"] is False


def _assert_404(r):
    assert r.status_code == 404 and r.json() == {}


def test_404_faelle(client, admin_headers, env, origin):
    _ready(client, env)
    _assert_404(_read(client, env["c"], env["o"].fp, "gibt-es-nicht")[0])           # unbekannt
    _assert_404(_read(client, env["c"], env["c"].fp)[0])                            # eigener Ursprung von C
    p = proto.new_catalog_read(env["o"].fp, "task", "o-1", "anna")                  # nicht in pull_users
    _assert_404(client.post(URL, json=p, headers=env["c"].headers(p)))
    _assert_404(_read(client, env["c"], env["o"].fp, item_kind="ticket")[0])
    push(client, env["o"], [], shared=False)                                        # O teilt nicht mehr
    _assert_404(_read(client, env["c"], env["o"].fp)[0])
    push(client, env["o"], [], shared=True)
    settings(client, admin_headers, shared=False)                                   # Hub teilt nicht
    _assert_404(_read(client, env["c"], env["o"].fp)[0])


def test_ohne_accept_oder_ohne_shared_beim_client(client, admin_headers, env, origin):
    _ready(client, env)
    push(client, env["c"], shared=False)
    _assert_404(_read(client, env["c"], env["o"].fp)[0])
    push(client, env["c"], shared=True)
    client.put(f"/api/federation/peers/{env['c_peer']['id']}/catalog", headers=admin_headers, json={"accept": False})
    _assert_404(_read(client, env["c"], env["o"].fp)[0])


def test_replay_frische_und_signatur(client, env, origin):
    _ready(client, env)
    r, p = _read(client, env["c"], env["o"].fp)
    assert r.status_code == 200
    _assert_404(client.post(URL, json=p, headers=env["c"].headers(p)))           # gleiche msg_id
    _assert_404(_read(client, env["c"], env["o"].fp, issued_at=int(time.time()) - 3600)[0])
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    p2 = proto.new_catalog_read(env["o"].fp, "task", "o-1", "testuser")
    _assert_404(client.post(URL, json=p2, headers=env["c"].headers(p2, key=Ed25519PrivateKey.generate())))
    p3 = {**proto.new_catalog_read(env["o"].fp, "task", "o-1", "testuser"), "msg_id": str(uuid.uuid4())}
    assert "seq" not in p3                                                         # ohne seq


def test_ablehnung_im_audit_ohne_inhalt(client, env, origin):
    _ready(client, env)
    _read(client, env["c"], env["o"].fp, "gibt-es-nicht")
    from hydrahive.db.connection import db
    with db() as conn:
        rows = [r[0] for r in conn.execute("SELECT error_message FROM errors_log WHERE source = 'federation.catalog'")]
    assert any("Lesen abgelehnt: unknown" in (m or "") for m in rows)
