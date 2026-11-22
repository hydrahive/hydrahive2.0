"""K2 — Ursprung beantwortet ``catalog_fetch`` (docs/specs/federation-catalog.md §Ablauf 4).

Dieser Test-Server ist der Client (Ursprung). Der Hub ist ein ``FakePeer`` mit
eigenem Schlüssel, gekoppelt und als Hub markiert. AK 10 (ausgeschlossenes
Projekt, nicht ausgewählter Nutzer → nicht abrufbar), „nur der eigene Hub“,
Replay, nach außen immer 404 ohne Code, Grund im Audit, signierte Antwort mit
``in_reply_to``, Kürzung auf MAX_TEXT.
"""
from __future__ import annotations

import time
import uuid

import pytest

from hydrahive.federation import catalog_origin, peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from hydrahive.modules import catalog_sources
from tests._catalog_fakes import FakeSource
from tests._own_rows import only_own_rows
from tests.test_federation_catalog_e1 import CATALOG_TABLES, _cleanup, _settings_body
from tests.test_peering_tasks import FakePeer

URL = "/api/peering/catalog/fetch"
T0 = "2026-11-21T10:00:00Z"


def _pair(client, admin_headers, name):
    fp = FakePeer(name)
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": fp.code()}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp.fp})
    return fp, peer


@pytest.fixture
def origin(client, admin_headers):
    _cleanup(client, admin_headers)
    catalog_origin._reset_for_tests()
    with only_own_rows(*CATALOG_TABLES, "errors_log"):
        hub_fp, hub_peer = _pair(client, admin_headers, "hydrahive-vps")
        assert client.put(f"/api/federation/peers/{hub_peer['id']}/hub", headers=admin_headers,
                          json={"is_hub": True}).status_code == 200
        client.put("/api/federation/catalog/settings", headers=admin_headers,
                   json=_settings_body(excluded_projects=["proj-geheim"]))
        tasks, ideas = FakeSource("task"), FakeSource("idea")
        snap = dict(catalog_sources.CATALOG_SOURCES)
        catalog_sources.CATALOG_SOURCES.clear()
        catalog_sources.CATALOG_SOURCES.update({"task": ("tasks", tasks.as_source()),
                                                "idea": ("scratchpad", ideas.as_source())})
        yield {"hub": hub_fp, "hub_peer": hub_peer, "tasks": tasks, "ideas": ideas}
        catalog_sources.CATALOG_SOURCES.clear()
        catalog_sources.CATALOG_SOURCES.update(snap)
        _cleanup(client, admin_headers)
        catalog_origin._reset_for_tests()


def _fetch(item_id="t-1", *, kind="task", owner="testuser", **over):
    p = {"kind": "catalog_fetch", "msg_id": str(uuid.uuid4()), "from": "x", "issued_at": int(time.time()),
         "item_kind": kind, "item_id": item_id, "owner": owner}
    p.update(over)
    return p


def _send(client, fp, payload, **kw):
    return client.post(URL, json=payload, headers=fp.headers(payload, **kw))


def _audit(text):
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT error_message FROM errors_log WHERE source = 'federation.catalog'").fetchall()
    return [r[0] for r in rows if text in (r[0] or "")]


def _is_plain_404(r):
    return r.status_code == 404 and r.json() == {}


# --- Erfolgsfall ----------------------------------------------------------------

def test_hub_bekommt_signierten_volltext_mit_in_reply_to(client, origin):
    origin["tasks"].put("t-1", T0, title="Rechnung")
    req = _fetch("t-1")
    r = _send(client, origin["hub"], req)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "catalog_item" and body["in_reply_to"] == req["msg_id"]
    assert ident.verify(ident.public_key_b64(), body, r.headers[proto.HEADER_SIGNATURE])
    assert body["item"]["description"] == "x" and body["item"]["title"] == "Rechnung"
    assert _audit("beantwortet")


def test_idee_mit_anmerkungen_und_kuerzung_auf_max_text(client, origin, monkeypatch):
    monkeypatch.setattr(proto, "MAX_TEXT", 10)
    origin["ideas"].put("i-1", T0)
    real = origin["ideas"].get_full

    def with_notes(username, item_id):
        full = real(username, item_id)
        return full and {**full, "body": "1234567", "notes": [{"author": "agent", "body": "abcdef", "created_at": T0}]}
    monkeypatch.setattr(origin["ideas"], "get_full", with_notes)
    catalog_sources.CATALOG_SOURCES["idea"] = ("scratchpad", origin["ideas"].as_source())
    r = _send(client, origin["hub"], _fetch("i-1", kind="idea"))
    item = r.json()["item"]
    assert item["body"] == "1234567" and item["notes"][0]["body"] == "abc"   # 7 + 3 = MAX_TEXT


# --- AK 10: ausgeschlossen / nicht ausgewählt / fremd → immer 404 ------------------

@pytest.mark.parametrize("case,reason", [
    ("projekt", "project_excluded"), ("nutzer", "user_not_selected"),
    ("fremd", "unknown"), ("unbekannt", "unknown"), ("art", "payload_invalid"),
])
def test_ak10_nicht_abrufbar_immer_gleich(client, origin, case, reason):
    origin["tasks"].put("t-geheim", T0, project_id="proj-geheim")
    origin["tasks"].put("t-anna", T0, owner="anna")
    req = {
        "projekt": _fetch("t-geheim"), "nutzer": _fetch("t-anna", owner="anna"),
        "fremd": _fetch("t-anna"), "unbekannt": _fetch("t-nix"), "art": _fetch("t-1", kind="note"),
    }[case]
    r = _send(client, origin["hub"], req)
    assert _is_plain_404(r)
    assert _audit(reason)


# --- Nur der eigene Hub, Sync an, Signatur, Frische, Replay -----------------------

def test_anderer_partner_ist_nicht_hub(client, admin_headers, origin):
    other, _ = _pair(client, admin_headers, "fremder-server")
    origin["tasks"].put("t-1", T0)
    assert _is_plain_404(_send(client, other, _fetch("t-1")))
    assert _audit("peer_not_hub")


def test_sync_aus(client, admin_headers, origin):
    client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(enabled=False))
    origin["tasks"].put("t-1", T0)
    assert _is_plain_404(_send(client, origin["hub"], _fetch("t-1")))
    assert _audit("peer_catalog_disabled")


def test_gesperrter_hub(client, admin_headers, origin):
    client.post(f"/api/federation/peers/{origin['hub_peer']['id']}/block", headers=admin_headers)
    origin["tasks"].put("t-1", T0)
    assert _is_plain_404(_send(client, origin["hub"], _fetch("t-1")))


def test_falsche_signatur_und_abgelaufen(client, origin):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    origin["tasks"].put("t-1", T0)
    assert _is_plain_404(_send(client, origin["hub"], _fetch("t-1"), key=Ed25519PrivateKey.generate()))
    assert _audit("peer_signature_invalid")
    assert _is_plain_404(_send(client, origin["hub"], _fetch("t-1", issued_at=int(time.time()) - 400)))
    assert _audit("peer_expired")


def test_replay_derselben_msg_id(client, origin):
    origin["tasks"].put("t-1", T0)
    req = _fetch("t-1")
    assert _send(client, origin["hub"], req).status_code == 200
    assert _is_plain_404(_send(client, origin["hub"], req))
    assert _audit("peer_replay")


def test_rate_limit(client, origin, monkeypatch):
    monkeypatch.setattr(catalog_origin, "_RATE_MAX", 1)
    origin["tasks"].put("t-1", T0)
    assert _send(client, origin["hub"], _fetch("t-1")).status_code == 200
    assert _is_plain_404(_send(client, origin["hub"], _fetch("t-1")))
    assert _audit("peer_rate_limited")


def test_unerwarteter_fehler_ebenfalls_404(client, origin, monkeypatch):
    """Review #738 L3: auch ein DB-Fehler am Ursprung sieht nach außen gleich aus."""
    from hydrahive.db import federation_catalog_client as client_db

    def broken():
        raise RuntimeError("DB weg")
    monkeypatch.setattr(client_db, "load_config", broken)
    assert _is_plain_404(_send(client, origin["hub"], _fetch("t-1")))
    assert _audit("error:RuntimeError")
