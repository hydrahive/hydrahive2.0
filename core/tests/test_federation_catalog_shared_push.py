"""V1 — shared/remote_edits im catalog_push (docs/specs/federation-shared-tasks.md
§Schalter: "Der Client meldet beide Werte in jedem catalog_push mit ... Der Hub
speichert sie in federation_catalog_sources."). Noch keine Löschzeilen bei
Wechsel (Auftrag B).
"""
from __future__ import annotations

import time
import uuid

import pytest

from hydrahive.federation import catalog_hub
from tests._own_rows import only_own_rows
from tests.test_peering_tasks import FakePeer

URL = "/api/peering/catalog/push"


def _push(seq, *, shared=None, remote_edits=None, **over):
    p = {"kind": "catalog_push", "msg_id": str(uuid.uuid4()), "from": "x", "seq": seq,
         "interval_seconds": 300, "issued_at": int(time.time()),
         "items": [], "deleted": [], "full_versions": None}
    if shared is not None:
        p["shared"] = shared
    if remote_edits is not None:
        p["remote_edits"] = remote_edits
    p.update(over)
    return p


@pytest.fixture
def hub(client, admin_headers):
    for p in client.get("/api/federation/peers", headers=admin_headers).json():
        client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)
    catalog_hub._rate.clear()
    fp = FakePeer("hydrahome")
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": fp.code()}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp.fp})
    r = client.put(f"/api/federation/peers/{peer['id']}/catalog", headers=admin_headers, json={"accept": True})
    assert r.status_code == 200, r.text
    with only_own_rows("errors_log"):
        yield fp, peer
    client.delete(f"/api/federation/peers/{peer['id']}", headers=admin_headers)
    catalog_hub._rate.clear()


def _send(client, fp, payload, **kw):
    return client.post(URL, json=payload, headers=fp.headers(payload, **kw))


def _source(peer_id):
    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute(
            "SELECT shared, remote_edits FROM federation_catalog_sources WHERE peer_id = ?", (peer_id,),
        ).fetchone()
    return dict(row) if row else None


def _code(r):
    return r.json()["detail"]["code"]


def test_push_mit_beiden_werten_wird_gespeichert(client, hub):
    fp, peer = hub
    r = _send(client, fp, _push(1, shared=True, remote_edits=True))
    assert r.status_code == 200, r.text
    assert _source(peer["id"]) == {"shared": 1, "remote_edits": 1}


def test_aelterer_client_ohne_felder_ergibt_0(client, hub):
    fp, peer = hub
    push = _push(1)
    # altes catalog_push ohne shared/remote_edits (Feld fehlt ganz, nicht nur None)
    assert "shared" not in push and "remote_edits" not in push
    r = _send(client, fp, push)
    assert r.status_code == 200, r.text
    assert _source(peer["id"]) == {"shared": 0, "remote_edits": 0}


def test_wechsel_von_true_auf_false_wird_uebernommen(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, shared=True, remote_edits=False))
    assert _source(peer["id"]) == {"shared": 1, "remote_edits": 0}
    _send(client, fp, _push(2, shared=False, remote_edits=False))
    assert _source(peer["id"]) == {"shared": 0, "remote_edits": 0}


@pytest.mark.parametrize("field", ["shared", "remote_edits"])
def test_ungueltiger_typ_wird_abgelehnt(client, hub, field):
    fp, peer = hub
    push = _push(1)
    push[field] = "ja"  # kein bool
    r = _send(client, fp, push)
    assert r.status_code == 400 and _code(r) == "peer_payload_invalid"
    assert _source(peer["id"]) is None  # nichts verbucht


def test_new_catalog_push_meldet_shared_und_remote_edits():
    from hydrahive.federation import peer_protocol as proto

    p = proto.new_catalog_push(7, 300, [], [], None, shared=True, remote_edits=False)
    assert p["shared"] is True
    assert p["remote_edits"] is False

    default = proto.new_catalog_push(8, 300, [], [], None)
    assert default["shared"] is False
    assert default["remote_edits"] is False
