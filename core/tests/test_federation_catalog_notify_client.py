"""G2/V7 — Client-Route POST /api/peering/catalog/notify (docs/specs/federation-shared-tasks.md
§Anstupsen): nur der eigene, aktive Hub; Signatur, Frische, msg_id neu; sonst nach außen
immer 404 mit Grund im Audit; ein Anstupser löst gebündelt genau ein Abholen aus.
"""
from __future__ import annotations

import asyncio
import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive.db.connection import db
from hydrahive.federation import catalog_notify_client as nc
from hydrahive.federation import catalog_pull_client
from tests._own_rows import only_own_rows
from tests.test_peering_tasks import FakePeer

URL = "/api/peering/catalog/notify"


@pytest.fixture
def hub(client, admin_headers, monkeypatch):
    """Dieser Server ist Client; ``vps`` ist sein Hub."""
    for p in client.get("/api/federation/peers", headers=admin_headers).json():
        client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)
    nc._reset_for_tests()
    pulls: list[str] = []

    async def fake_pull(*, full=None, reason="timer"):
        pulls.append(reason)
        await asyncio.sleep(0)
        return "ok"
    monkeypatch.setattr(catalog_pull_client, "pull", fake_pull)
    fp = FakePeer("vps")
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": fp.code()}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp.fp})
    r = client.put(f"/api/federation/peers/{peer['id']}/hub", headers=admin_headers, json={"is_hub": True})
    assert r.status_code == 200, r.text
    with only_own_rows("errors_log"):
        yield fp, peer, pulls
    client.delete(f"/api/federation/peers/{peer['id']}", headers=admin_headers)
    nc._reset_for_tests()


def _note(**over):
    p = {"kind": "catalog_notify", "msg_id": str(uuid.uuid4()), "from": "x", "issued_at": int(time.time()), "rev": 7}
    p.update(over)
    return p


def _send(client, fp, payload, **kw):
    return client.post(URL, json=payload, headers=fp.headers(payload, **kw))


def _audit(text):
    with db() as conn:
        rows = conn.execute("SELECT error_message FROM errors_log WHERE source = 'federation.catalog'").fetchall()
    return [r[0] for r in rows if text in (r[0] or "")]


async def _settle():
    for _ in range(20):
        await asyncio.sleep(0.01)


async def test_eigener_hub_wird_angenommen_und_holt_ab(client, hub):
    fp, _, pulls = hub
    r = await asyncio.to_thread(_send, client, fp, _note())
    assert r.status_code == 200 and r.json() == {"ok": True}
    await _settle()
    assert pulls == ["notify"]


def _assert_404(r):
    assert r.status_code == 404 and r.json() == {}            # kein Code, kein Grund nach außen


def test_fremder_partner_der_nicht_hub_ist(client, admin_headers, hub):
    other = FakePeer("anderer")
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": other.code()}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": other.fp})
    _assert_404(_send(client, other, _note()))
    assert _audit("Anstupsen abgelehnt: peer_not_hub")
    assert hub[2] == []


def test_unbekannter_absender_und_falsche_signatur(client, hub):
    fp, _, pulls = hub
    _assert_404(_send(client, FakePeer("fremd"), _note()))
    _assert_404(_send(client, fp, _note(), key=Ed25519PrivateKey.generate()))
    assert _audit("peer_unknown") and _audit("peer_signature_invalid") and pulls == []


def test_abgelaufen_falscher_typ_fehlende_felder(client, hub):
    fp, _, pulls = hub
    _assert_404(_send(client, fp, _note(issued_at=int(time.time()) - 3600)))
    _assert_404(_send(client, fp, _note(kind="catalog_push")))
    _assert_404(_send(client, fp, _note(msg_id="")))
    _assert_404(_send(client, fp, _note(rev="viel")))
    assert _audit("peer_expired") and _audit("payload_invalid") and pulls == []


def test_gesperrter_hub(client, admin_headers, hub):
    fp, peer, pulls = hub
    client.post(f"/api/federation/peers/{peer['id']}/block", headers=admin_headers)
    _assert_404(_send(client, fp, _note()))
    assert pulls == []


async def test_wiederholte_msg_id(client, hub):
    fp, _, pulls = hub
    note = _note()
    assert (await asyncio.to_thread(_send, client, fp, note)).status_code == 200
    _assert_404(await asyncio.to_thread(_send, client, fp, note))
    await _settle()
    assert _audit("peer_replay") and pulls == ["notify"]


async def test_viele_anstupser_buendeln_zu_einem_abholen_danach(monkeypatch):
    nc._reset_for_tests()
    gate = asyncio.Event()
    pulls: list[str] = []

    async def slow_pull(*, full=None, reason="timer"):
        pulls.append(reason)
        await gate.wait()
        return "ok"
    monkeypatch.setattr(catalog_pull_client, "pull", slow_pull)
    assert nc.trigger() is True                               # erstes Abholen läuft
    await asyncio.sleep(0)
    assert [nc.trigger() for _ in range(5)] == [False] * 5    # während des Laufs: nur vormerken
    gate.set()
    await _settle()
    assert pulls == ["notify", "notify"]                      # genau eines danach, nicht fünf
    assert nc.trigger() is True                               # danach wieder frei
    await _settle()
    assert len(pulls) == 3


async def test_route_wartet_nicht_auf_das_abholen(client, hub, monkeypatch):
    fp, _, _ = hub
    gate = asyncio.Event()

    async def hang(*, full=None, reason="timer"):
        await gate.wait()
        return "ok"
    monkeypatch.setattr(catalog_pull_client, "pull", hang)
    r = await asyncio.wait_for(asyncio.to_thread(_send, client, fp, _note()), timeout=5)
    assert r.status_code == 200
    gate.set()
    await _settle()


def test_pfad_liegt_unter_tailnet_sperre():
    assert URL.startswith("/api/peering/")
