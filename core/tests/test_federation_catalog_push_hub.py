"""S1 — Hub nimmt ``catalog_push`` an (docs/specs/federation-catalog.md §Ablauf 3).

Akzeptanzkriterien: 2 (Hub-Seite: ohne catalog_accept kommt nichts an),
8 (gefälschte Signatur, alte/falsche seq, abgelaufene Nachricht → abgelehnt
und im Audit), 12 (Partner entfernen → Einträge weg, sperren → keine Annahme).
Dazu Upsert nur bei updated_at ≥ gespeichert, deleted, full_versions mit
resync und federation_catalog_rejected.
"""
from __future__ import annotations

import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive.federation import catalog_hub
from tests._own_rows import only_own_rows
from tests.test_peering_tasks import FakePeer

URL = "/api/peering/catalog/push"
T0 = "2026-11-21T10:00:00Z"
T1 = "2026-11-21T10:00:01Z"


def _item(item_id="t-1", *, kind="task", status="open", updated_at=T0, owner="till", **over):
    item = {"kind": kind, "item_id": item_id, "owner": owner, "title": f"Titel {item_id}",
            "status": status, "priority": "medium" if kind == "task" else None,
            "project_id": None, "project_name": None, "created_at": T0, "updated_at": updated_at}
    item.update(over)
    return item


def _push(seq, items=(), deleted=(), full=None, **over):
    p = {"kind": "catalog_push", "msg_id": str(uuid.uuid4()), "from": "x", "seq": seq,
         "interval_seconds": 300, "issued_at": int(time.time()),
         "items": list(items), "deleted": list(deleted), "full_versions": full}
    p.update(over)
    return p


@pytest.fixture
def hub(client, admin_headers):
    """Gekoppelter Partner (Client), dessen Katalog dieser Server annimmt."""
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


def _rows(peer_id):
    from hydrahive.db.connection import db
    with db() as conn:
        return {r["item_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM federation_catalog_items WHERE peer_id = ? ORDER BY item_id", (peer_id,))}


def _audit(text):
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute(
            "SELECT error_message FROM errors_log WHERE source = 'federation.catalog'").fetchall()
    return [r[0] for r in rows if text in (r[0] or "")]


def _code(r):
    return r.json()["detail"]["code"]


# --- Annahme ------------------------------------------------------------------

def test_push_wird_angenommen_nur_metadaten(client, hub):
    fp, peer = hub
    r = _send(client, fp, _push(1, [_item("t-1"), _item("i-1", kind="idea", status="new")]))
    assert r.status_code == 200, r.text
    assert r.json() == {"ack_seq": 1, "resync": []}
    rows = _rows(peer["id"])
    assert set(rows) == {"i-1", "t-1"}
    assert rows["t-1"]["owner"] == "till" and rows["t-1"]["snapshot_body"] is None
    assert "description" not in rows["t-1"] and "body" not in rows["t-1"]  # AK 6: nur Metadaten
    assert _audit("Push seq 1 angenommen: 2 Einträge")
    assert "Titel" not in _audit("Push seq 1")[0]  # Audit ohne Titel


def test_leerer_push_ist_lebenszeichen_ohne_audit(client, hub):
    fp, peer = hub
    assert _send(client, fp, _push(1)).json() == {"ack_seq": 1, "resync": []}
    assert _audit("Push seq 1") == []
    from hydrahive.db import federation_peers as peers_db
    assert peers_db.get_peer(peer["id"])["last_seen"]


def test_upsert_nur_bei_updated_at_groesser_gleich_und_snapshot_veraltet(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1", updated_at=T1, title="neu")]))
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE federation_catalog_items SET snapshot_body = 'alt', snapshot_stale = 0 "
                     "WHERE item_id = 't-1'")
    _send(client, fp, _push(2, [_item("t-1", updated_at=T0, title="älter")]))       # älter → ignoriert
    assert _rows(peer["id"])["t-1"]["title"] == "neu"
    _send(client, fp, _push(3, [_item("t-1", updated_at=T1, title="gleich alt")]))  # gleich → überschreiben
    row = _rows(peer["id"])["t-1"]
    assert row["title"] == "gleich alt" and row["snapshot_stale"] == 0
    _send(client, fp, _push(4, [_item("t-1", updated_at="2026-11-21T10:00:02Z")]))   # neuer → Snapshot veraltet
    row = _rows(peer["id"])["t-1"]
    assert row["snapshot_body"] == "alt" and row["snapshot_stale"] == 1


def test_deleted_entfernt_eintrag(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1"), _item("t-2")]))
    r = _send(client, fp, _push(2, deleted=[{"kind": "task", "item_id": "t-1"}]))
    assert r.status_code == 200
    assert set(_rows(peer["id"])) == {"t-2"}


def test_ungueltige_eintraege_einzeln_verworfen_und_gemerkt(client, hub):
    fp, peer = hub
    bad = [_item("t-bad", status="new"), _item("x-1", kind="note"), _item("t-long", title="x" * 301), "kaputt"]
    r = _send(client, fp, _push(1, [_item("t-ok"), *bad]))
    assert r.status_code == 200
    assert set(_rows(peer["id"])) == {"t-ok"}
    from hydrahive.db.connection import db
    with db() as conn:
        rej = {r["item_id"]: r["reason"] for r in conn.execute(
            "SELECT item_id, reason FROM federation_catalog_rejected WHERE peer_id = ?", (peer["id"],))}
    assert rej == {"t-bad": "status_invalid", "t-long": "title_too_long"}
    assert _audit("4 verworfen")  # 3 mit Grund + 1 unlesbarer Eintrag


def test_full_versions_entfernt_fehlende_und_meldet_resync(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1"), _item("t-2"), _item("i-1", kind="idea", status="new")]))
    full = {"till": {"task": [["t-1", T0], ["t-3", T0]], "idea": [["i-1", T0]]}}
    r = _send(client, fp, _push(2, full=full))
    assert r.status_code == 200
    assert r.json()["resync"] == [{"username": "till", "kind": "task"}]  # t-3 fehlt dem Hub
    assert set(_rows(peer["id"])) == {"i-1", "t-1"}                       # t-2 fehlt in der Liste → weg
    full = {"till": {"task": [["t-1", T1]], "idea": [["i-1", T0]]}}
    assert _send(client, fp, _push(3, full=full)).json()["resync"] == [{"username": "till", "kind": "task"}]


def test_full_versions_verworfene_loesen_kein_resync_aus(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1"), _item("t-bad", status="kaputt")]))
    full = {"till": {"task": [["t-1", T0], ["t-bad", T0]]}}
    assert _send(client, fp, _push(2, full=full)).json()["resync"] == []
    full = {"till": {"task": [["t-1", T0], ["t-bad", T1]]}}  # updated_at geändert → wieder anfordern
    assert _send(client, fp, _push(3, full=full)).json()["resync"] == [{"username": "till", "kind": "task"}]


def test_full_versions_ohne_nutzer_leert_dessen_eintraege(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1"), _item("t-anna", owner="anna")]))
    _send(client, fp, _push(2, full={"till": {"task": [["t-1", T0]]}}))
    assert set(_rows(peer["id"])) == {"t-1"}


def test_full_versions_unlesbar_lehnt_ganze_nachricht_ab(client, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1")]))
    r = _send(client, fp, _push(2, full={"till": {"task": [["t-1"]]}}))
    assert r.status_code == 400 and _code(r) == "peer_payload_invalid"
    assert set(_rows(peer["id"])) == {"t-1"}


# --- AK 2 (Hub-Seite): ohne catalog_accept kommt nichts an ----------------

def test_ohne_catalog_accept_abgelehnt(client, admin_headers, hub):
    fp, peer = hub
    client.put(f"/api/federation/peers/{peer['id']}/catalog", headers=admin_headers, json={"accept": False})
    r = _send(client, fp, _push(1, [_item()]))
    assert r.status_code == 403 and _code(r) == "peer_catalog_not_accepted"
    assert _rows(peer["id"]) == {}
    assert _audit("peer_catalog_not_accepted")


# --- AK 8: Signatur, seq, Frische ---------------------------------------------

def test_gefaelschte_signatur(client, hub):
    fp, peer = hub
    r = _send(client, fp, _push(1, [_item()]), key=Ed25519PrivateKey.generate())
    assert r.status_code == 403 and _code(r) == "peer_signature_invalid"
    assert _rows(peer["id"]) == {} and _audit("peer_signature_invalid")


def test_unbekannter_absender(client, hub):
    r = _send(client, FakePeer("fremd"), _push(1, [_item()]))
    assert r.status_code == 403 and _code(r) == "peer_unknown"
    assert _audit("peer_unknown")


def test_abgelaufene_nachricht(client, hub):
    fp, peer = hub
    r = _send(client, fp, _push(1, [_item()], issued_at=int(time.time()) - 400))
    assert r.status_code == 403 and _code(r) == "peer_expired"
    assert _audit("peer_expired")


def test_alte_und_gleiche_seq_abgelehnt_mit_last_seq(client, hub):
    fp, peer = hub
    assert _send(client, fp, _push(5)).status_code == 200
    for seq in (5, 4):
        r = _send(client, fp, _push(seq, [_item()]))
        assert r.status_code == 409 and _code(r) == "peer_replay"
        assert r.json()["detail"]["params"] == {"last_seq": 5}
    assert _rows(peer["id"]) == {} and _audit("peer_replay")
    assert _send(client, fp, _push(6, [_item()])).status_code == 200  # last_seq + 1 geht


def test_msg_id_pflicht_und_falscher_typ(client, hub):
    fp, _ = hub
    p = _push(1)
    del p["msg_id"]
    assert _code(_send(client, fp, p)) == "peer_payload_invalid"
    assert _code(_send(client, fp, _push(1, kind="task"))) == "peer_payload_invalid"


def test_rate_limit_eigener_zaehler(client, hub, monkeypatch):
    fp, _ = hub
    monkeypatch.setattr(catalog_hub, "_RATE_MAX", 2)
    assert _send(client, fp, _push(1)).status_code == 200
    assert _send(client, fp, _push(2)).status_code == 200
    r = _send(client, fp, _push(3))
    assert r.status_code == 429 and _code(r) == "peer_rate_limited"
    from hydrahive.federation import peer_inbound
    assert fp and not peer_inbound._rate.get(hub[1]["id"])  # Auftrags-Zähler unberührt


def test_zu_viele_eintraege(client, hub):
    fp, _ = hub
    r = _send(client, fp, _push(1, [_item(f"t-{i}") for i in range(501)]))
    assert r.status_code == 400 and _code(r) == "peer_payload_too_large"


# --- AK 12: Partner entfernen / sperren ------------------------------------

def test_partner_entfernen_loescht_eintraege(client, admin_headers, hub):
    fp, peer = hub
    _send(client, fp, _push(1, [_item("t-1")]))
    assert _rows(peer["id"])
    client.delete(f"/api/federation/peers/{peer['id']}", headers=admin_headers)
    assert _rows(peer["id"]) == {}


def test_partner_sperren_keine_annahme(client, admin_headers, hub):
    fp, peer = hub
    client.post(f"/api/federation/peers/{peer['id']}/block", headers=admin_headers)
    r = _send(client, fp, _push(1, [_item()]))
    assert r.status_code == 403 and _code(r) == "peer_unknown"
    assert _rows(peer["id"]) == {}


# --- verify_incoming: task/reply unverändert ---------------------------------

def test_verify_incoming_standard_bleibt_task_id(client, hub):
    from hydrahive.federation import peer_protocol as proto
    fp, _ = hub
    payload = {"kind": "reply", "task_id": "", "issued_at": int(time.time())}
    with pytest.raises(proto.PeerRejected) as exc:
        proto.verify_incoming(fp.fp, fp.headers(payload)[proto.HEADER_SIGNATURE], payload, "reply")
    assert "task_id" in str(exc.value)
    payload = {"kind": "catalog_push", "msg_id": "m-1", "issued_at": int(time.time())}
    ok = proto.verify_incoming(fp.fp, fp.headers(payload)[proto.HEADER_SIGNATURE], payload,
                               "catalog_push", id_field="msg_id")
    assert ok.payload["msg_id"] == "m-1"


def test_new_catalog_push_form():
    from hydrahive.federation import peer_protocol as proto
    p = proto.new_catalog_push(7, 300, [_item()], [{"kind": "task", "item_id": "t-9"}], None)
    assert p["kind"] == "catalog_push" and p["seq"] == 7 and p["interval_seconds"] == 300
    assert isinstance(p["msg_id"], str) and isinstance(p["issued_at"], int)
    assert p["full_versions"] is None and len(p["items"]) == 1


def test_catalog_pfad_liegt_unter_tailnet_sperre():
    """AK 9 vorbereitet: /api/peering/catalog/* fällt unter location /api/peering/ (nginx)."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    for script in ("installer/modules/60-nginx.sh", "installer/modules-mac/60-nginx.sh"):
        text = (root / script).read_text()
        assert "location /api/peering/ {" in text
    assert URL.startswith("/api/peering/")
