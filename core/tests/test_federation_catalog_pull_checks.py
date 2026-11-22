"""G2/V2 — catalog_pull: Prüfreihenfolge, Ablehnungen, Signatur der Antwort
(docs/specs/federation-shared-tasks.md §Nachricht catalog_pull, §Schalter).
"""
from __future__ import annotations

import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive.db.connection import db
from hydrahive.federation import catalog_hub, peer_identity as ident, peer_protocol as proto
from tests._catalog_pull_env import PULL, code, pull, pull_payload, push, settings, verified
from tests.test_peering_tasks import FakePeer

pytest_plugins = ["tests._catalog_pull_env"]  # Fixture `env`


def test_antwort_ist_signiert_mit_in_reply_to(client, env):
    r, p = pull(client, env["c"])
    body = verified(r, p)                                       # wirft bei falscher Signatur
    assert body["kind"] == "catalog_items" and body["in_reply_to"] == p["msg_id"]
    assert body["ack_seq"] == p["seq"]
    for key in ("items", "deleted", "next_rev", "local_next", "more", "reset_local", "full_keys", "instances"):
        assert key in body


def test_manipulierte_antwort_faellt_durch(client, env):
    r, p = pull(client, env["c"])
    body = r.json()
    body["items"] = [{"item_id": "untergeschoben"}]
    hub_peer = {"name": "hub", "public_key": ident.public_key_b64()}
    try:
        proto.verify_reply(hub_peer, r.headers[proto.HEADER_SIGNATURE], body, "catalog_items", p["msg_id"])
    except proto.PeerRejected as e:
        assert e.code == "peer_signature_invalid"
    else:
        raise AssertionError("manipulierte Antwort wurde angenommen")


def test_unbekannter_absender_und_falsche_signatur(client, env):
    fremd = FakePeer("fremd")
    p = pull_payload(fremd)
    r = client.post(PULL, json=p, headers=fremd.headers(p))
    assert r.status_code == 403 and code(r) == "peer_unknown"
    p = pull_payload(env["c"])
    r = client.post(PULL, json=p, headers=env["c"].headers(p, key=Ed25519PrivateKey.generate()))
    assert code(r) == "peer_signature_invalid"


def test_abgelaufen_und_falscher_typ(client, env):
    p = pull_payload(env["c"], issued_at=int(time.time()) - 3600)
    assert code(client.post(PULL, json=p, headers=env["c"].headers(p))) == "peer_expired"
    p = pull_payload(env["c"], kind="catalog_push")
    assert code(client.post(PULL, json=p, headers=env["c"].headers(p))) == "peer_payload_invalid"


def test_ohne_catalog_accept_not_accepted_vor_seq(client, admin_headers, env):
    client.put(f"/api/federation/peers/{env['c_peer']['id']}/catalog", headers=admin_headers, json={"accept": False})
    p = pull_payload(env["c"], seq=1)                            # alte seq: accept wird ZUERST geprüft
    r = client.post(PULL, json=p, headers=env["c"].headers(p))
    assert r.status_code == 403 and code(r) == "peer_catalog_not_accepted"


def test_seq_gemeinsam_mit_push(client, env):
    r, p = pull(client, env["c"])
    assert r.status_code == 200
    stale = pull_payload(env["c"], seq=p["seq"])                 # gleiche seq noch einmal
    r = client.post(PULL, json=stale, headers=env["c"].headers(stale))
    assert r.status_code == 409 and r.json()["detail"]["params"]["last_seq"] == p["seq"]
    # ein Push mit derselben seq ist ebenfalls verbraucht
    push_p = {"kind": "catalog_push", "msg_id": "m", "from": "x", "seq": p["seq"], "interval_seconds": 300,
              "issued_at": int(time.time()), "items": [], "deleted": [], "full_versions": None}
    r = client.post("/api/peering/catalog/push", json=push_p, headers=env["c"].headers(push_p))
    assert r.status_code == 409
    push(client, env["c"])                                       # nächste seq geht wieder
    assert pull(client, env["c"])[0].status_code == 200


def test_rate_limit_gemeinsam_mit_push(client, env, monkeypatch):
    monkeypatch.setattr(catalog_hub, "_RATE_MAX", 2)
    catalog_hub._rate.clear()
    assert pull(client, env["c"])[0].status_code == 200
    push(client, env["c"])
    r, _ = pull(client, env["c"])
    assert r.status_code == 429 and code(r) == "peer_rate_limited"


def test_hub_ohne_shared_not_shared(client, admin_headers, env):
    settings(client, admin_headers, shared=False)
    r, _ = pull(client, env["c"])
    assert r.status_code == 403 and code(r) == "peer_catalog_not_shared"


def test_client_ohne_shared_not_shared(client, env):
    push(client, env["c"], shared=False)
    r, _ = pull(client, env["c"])
    assert code(r) == "peer_catalog_not_shared"


def test_client_hat_nie_gepusht_not_shared(client, admin_headers, env):
    from tests._catalog_pull_env import _pair
    neu_fp, neu = _pair(client, admin_headers, "neuling")
    r, _ = pull(client, neu_fp)
    assert code(r) == "peer_catalog_not_shared"
    client.delete(f"/api/federation/peers/{neu['id']}", headers=admin_headers)


def test_gesperrter_client_wird_abgewiesen(client, admin_headers, env):
    client.post(f"/api/federation/peers/{env['c_peer']['id']}/block", headers=admin_headers)
    r, _ = pull(client, env["c"])
    assert r.status_code == 403 and code(r) == "peer_unknown"


def test_ungueltige_felder(client, env):
    for over in ({"users": "till"}, {"users": [1]}, {"after_rev": -1}, {"after_rev": True},
                 {"limit": 0}, {"local_after": {"task": ["nur-eins"]}}, {"local_after": []},
                 {"keys_after": ["a", "b"]}):
        p = pull_payload(env["c"])
        p.update(over)                                           # nach dem Aufbau, ohne list()
        r = client.post(PULL, json=p, headers=env["c"].headers(p))
        assert r.status_code == 400 and code(r) == "peer_payload_invalid", over


def test_pull_users_und_last_pull_at_gespeichert(client, env):
    pull(client, env["c"], users=["testuser", "anna", "testuser"])
    with db() as conn:
        row = conn.execute("SELECT pull_users, last_pull_at FROM federation_catalog_sources WHERE peer_id = ?",
                           (env["c_peer"]["id"],)).fetchone()
    assert row["pull_users"] == '["anna", "testuser"]' and row["last_pull_at"]


def test_ablehnung_steht_im_audit(client, admin_headers, env):
    settings(client, admin_headers, shared=False)
    pull(client, env["c"])
    with db() as conn:
        rows = conn.execute("SELECT error_message FROM errors_log WHERE source = 'federation.catalog'").fetchall()
    assert any("Abholen abgelehnt: peer_catalog_not_shared" in (r[0] or "") for r in rows)


def test_new_catalog_pull_form():
    p = proto.new_catalog_pull(5, ["testuser"], 7, {"task": None, "idea": None}, full=True)
    assert p["kind"] == "catalog_pull" and p["seq"] == 5 and p["after_rev"] == 7 and p["full"] is True
    assert p["msg_id"] and p["limit"] == 500
