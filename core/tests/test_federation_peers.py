"""Server-Kopplung Etappe 1 (docs/specs/server-peering.md): Identität,
Kopplungscode, Partner anlegen, Fingerprint-Bestätigung, Freigaben."""
from __future__ import annotations

import base64
import stat

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive.federation import peer_identity as ident


def _foreign_code(name: str = "vps") -> tuple[str, str]:
    """Kopplungscode eines fremden Servers (eigener Schlüssel) + Fingerprint."""
    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    body = {"name": name, "url": f"https://{name}.example", "public_key": pub}
    code = "hhpeer1:" + base64.urlsafe_b64encode(ident.canonical(body)).decode()
    return code, ident.fingerprint(pub)


def _cleanup(client, admin_headers):
    for p in client.get("/api/federation/peers", headers=admin_headers).json():
        client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)


# --- Identität -------------------------------------------------------------

def test_key_is_created_private_and_stable(client):
    first = ident.public_key_b64()
    assert ident.public_key_b64() == first
    mode = stat.S_IMODE(ident._key_path().stat().st_mode)
    assert mode == 0o600


def test_sign_verify_roundtrip_and_tamper():
    payload = {"task": "x", "n": 1}
    sig = ident.sign(payload)
    pub = ident.public_key_b64()
    assert ident.verify(pub, payload, sig)
    assert not ident.verify(pub, {"task": "y", "n": 1}, sig)
    other_code, _ = _foreign_code()
    other_pub = ident.parse_pairing_code(other_code)["public_key"]
    assert not ident.verify(other_pub, payload, sig)
    assert not ident.verify(pub, payload, "kaputt")


def test_pairing_code_roundtrip_and_rejects_garbage():
    code = ident.pairing_code("home", "https://100.84.107.19/")
    info = ident.parse_pairing_code(code)
    assert info == {"name": "home", "url": "https://100.84.107.19", "public_key": ident.public_key_b64()}
    for bad in ("", "abc", "hhpeer1:!!!", "hhpeer1:" + base64.urlsafe_b64encode(b'{"name":"x"}').decode()):
        try:
            ident.parse_pairing_code(bad)
        except ValueError:
            continue
        raise AssertionError(f"angenommen: {bad!r}")


# --- API -------------------------------------------------------------------

def test_requires_admin(client, auth_headers):
    assert client.get("/api/federation/peers", headers=auth_headers).status_code in (401, 403)
    assert client.get("/api/federation/peers").status_code == 401


def test_own_code_never_leaks_private_key(client, admin_headers):
    r = client.post(
        "/api/federation/peers/identity/code", headers=admin_headers,
        json={"name": "home", "url": "https://100.84.107.19"},
    )
    assert r.status_code == 200
    assert "PRIVATE" not in r.text
    assert ident.parse_pairing_code(r.json()["code"])["public_key"] == ident.public_key_b64()


def test_pair_confirm_and_agents_flow(client, admin_headers):
    _cleanup(client, admin_headers)
    code, fp = _foreign_code()
    r = client.post("/api/federation/peers", headers=admin_headers, json={"code": code})
    assert r.status_code == 201, r.text
    peer = r.json()
    assert peer["status"] == "pending"
    assert "public_key" not in peer
    assert peer["allowed_agents"] == []

    bad = client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers,
                      json={"fingerprint": "0000 0000"})
    assert bad.status_code == 400
    assert client.get("/api/federation/peers", headers=admin_headers).json()[0]["status"] == "pending"

    ok = client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers,
                     json={"fingerprint": fp.upper()})
    assert ok.status_code == 200
    assert ok.json()["status"] == "active"
    assert ok.json()["confirmed_at"]

    unknown = client.put(f"/api/federation/peers/{peer['id']}/agents", headers=admin_headers,
                         json={"agent_ids": ["gibt-es-nicht"]})
    assert unknown.status_code == 400

    blocked = client.post(f"/api/federation/peers/{peer['id']}/block", headers=admin_headers)
    assert blocked.json()["status"] == "blocked"

    assert client.delete(f"/api/federation/peers/{peer['id']}", headers=admin_headers).status_code == 204
    assert client.get("/api/federation/peers", headers=admin_headers).json() == []


def test_rejects_own_code_duplicates_and_http(client, admin_headers):
    _cleanup(client, admin_headers)
    own = ident.pairing_code("home", "https://x.example")
    assert client.post("/api/federation/peers", headers=admin_headers, json={"code": own}).status_code == 400

    code, _ = _foreign_code("dup")
    assert client.post("/api/federation/peers", headers=admin_headers, json={"code": code}).status_code == 201
    assert client.post("/api/federation/peers", headers=admin_headers, json={"code": code}).status_code == 409

    info = ident.parse_pairing_code(_foreign_code("plain")[0])
    info["url"] = "http://plain.example"
    plain = "hhpeer1:" + base64.urlsafe_b64encode(ident.canonical(info)).decode()
    assert client.post("/api/federation/peers", headers=admin_headers, json={"code": plain}).status_code == 400
    _cleanup(client, admin_headers)
