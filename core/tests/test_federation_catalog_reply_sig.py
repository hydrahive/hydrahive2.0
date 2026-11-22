"""K2 — Ergänzung zu send_signed: signierte Antwort prüfen (request_signed / verify_reply).

Der Hub vertraut der Antwort nur, wenn sie mit dem Schlüssel des Ursprungs
signiert ist, ``kind = catalog_item`` hat, frisch ist und ``in_reply_to`` seine
eigene Anfrage nennt. HTTP wird über httpx.MockTransport gefälscht.
"""
from __future__ import annotations

import base64
import time

import httpx
import pytest

from hydrahive.federation import peer_identity as ident
from hydrahive.federation import peer_outbound
from hydrahive.federation import peer_protocol as proto
from tests.test_peering_tasks import FakePeer


@pytest.fixture
def origin(monkeypatch):
    fp = FakePeer("hydrahome")
    peer = {"name": "hydrahome", "url": "https://hydrahome.example", "public_key": fp.pub}
    state = {"reply": None, "status": 200, "key": fp.key, "seen": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["seen"].append(request)
        if state["status"] != 200:
            return httpx.Response(state["status"], json={})
        body = state["reply"]
        sig = base64.b64encode(state["key"].sign(ident.canonical(body))).decode()
        return httpx.Response(200, json=body, headers={proto.HEADER_SIGNATURE: sig})

    real_client = httpx.AsyncClient

    def client_factory(*a, **kw):
        kw.pop("verify", None)
        return real_client(*a, transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(peer_outbound.httpx, "AsyncClient", client_factory)
    return peer, state


def _reply(req, **over):
    body = {"kind": "catalog_item", "msg_id": "r-1", "in_reply_to": req["msg_id"], "from": "x",
            "issued_at": int(time.time()), "item": {"item_id": "t-1"}}
    body.update(over)
    return body


async def _ask(peer):
    req = proto.new_catalog_fetch("task", "t-1", "till")
    return req, peer_outbound.request_signed(peer, "/api/peering/catalog/fetch", req,
                                             reply_kind="catalog_item", timeout=10.0)


async def test_gueltige_antwort_wird_angenommen(origin):
    peer, state = origin
    req, call = await _ask(peer)
    state["reply"] = _reply(req)
    reply = await call
    assert reply["item"] == {"item_id": "t-1"}
    sent = state["seen"][0]
    assert sent.headers[proto.HEADER_SIGNATURE] and sent.url.path == "/api/peering/catalog/fetch"


@pytest.mark.parametrize("change,code", [
    ({"in_reply_to": "fremde-anfrage"}, "peer_payload_invalid"),
    ({"kind": "catalog_push"}, "peer_payload_invalid"),
    ({"issued_at": 1}, "peer_expired"),
])
async def test_ungueltige_antwort_abgelehnt(origin, change, code):
    peer, state = origin
    req, call = await _ask(peer)
    state["reply"] = _reply(req, **change)
    with pytest.raises(proto.PeerRejected) as exc:
        await call
    assert exc.value.code == code


async def test_fremder_schluessel_abgelehnt(origin):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    peer, state = origin
    state["key"] = Ed25519PrivateKey.generate()
    req, call = await _ask(peer)
    state["reply"] = _reply(req)
    with pytest.raises(proto.PeerRejected) as exc:
        await call
    assert exc.value.code == "peer_signature_invalid"


async def test_404_heisst_nicht_verfuegbar(origin):
    peer, state = origin
    state["status"] = 404
    _req, call = await _ask(peer)
    with pytest.raises(peer_outbound.ReplyUnavailable):
        await call


async def test_serverfehler_ist_netzfehler(origin):
    peer, state = origin
    state["status"] = 502
    _req, call = await _ask(peer)
    with pytest.raises(httpx.HTTPStatusError):
        await call


def test_new_catalog_fetch_und_item_form():
    req = proto.new_catalog_fetch("idea", "i-1", "till")
    assert set(req) == {"kind", "msg_id", "from", "issued_at", "item_kind", "item_id", "owner"}
    item = proto.new_catalog_item(req["msg_id"], {"item_id": "i-1"})
    assert item["kind"] == "catalog_item" and item["in_reply_to"] == req["msg_id"]


# --- Größengrenze der Antwort (Security-Review #738, MEDIUM) ------------------------

def test_grenze_reicht_fuer_gueltige_antwort():
    # MAX_TEXT Zeichen à 4 Byte (UTF-8 ohne Escape) plus Metadaten passen hinein
    assert peer_outbound.MAX_REPLY_BYTES >= 4 * proto.MAX_TEXT + 64 * 1024


async def test_grosse_gueltige_antwort_mit_umlauten_wird_angenommen(origin):
    peer, state = origin
    req, call = await _ask(peer)
    text = "ä" * proto.MAX_TEXT                        # 2 Byte je Zeichen, ohne Escape
    state["reply"] = _reply(req, item={"item_id": "t-1", "description": text})
    reply = await call
    assert len(reply["item"]["description"]) == proto.MAX_TEXT


@pytest.fixture
def raw_origin(monkeypatch):
    """Ursprung, der rohe Bytes mit frei wählbaren Headern liefert (auch ohne Content-Length)."""
    state = {"content": b"", "headers": {}, "stream": False}

    class _Chunks(httpx.AsyncByteStream):
        def __init__(self, data: bytes) -> None:
            self.data = data

        async def __aiter__(self):
            for i in range(0, len(self.data), 65_536):
                yield self.data[i:i + 65_536]

    def handler(request: httpx.Request) -> httpx.Response:
        if state["stream"]:                              # chunked: keine Content-Length
            return httpx.Response(200, headers=state["headers"], stream=_Chunks(state["content"]))
        return httpx.Response(200, headers=state["headers"], content=state["content"])

    real_client = httpx.AsyncClient

    def client_factory(*a, **kw):
        kw.pop("verify", None)
        return real_client(*a, transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(peer_outbound.httpx, "AsyncClient", client_factory)
    peer = {"name": "boese", "url": "https://boese.example", "public_key": FakePeer("boese").pub}
    return peer, state


@pytest.mark.parametrize("stream", [False, True], ids=["content-length", "chunked"])
async def test_zu_grosse_antwort_wird_abgebrochen(raw_origin, stream):
    peer, state = raw_origin
    state["content"] = b"{" + b" " * (peer_outbound.MAX_REPLY_BYTES + 1) + b"}"
    state["stream"] = stream
    _req, call = await _ask(peer)
    with pytest.raises(proto.PeerRejected) as exc:
        await call
    assert exc.value.code == "peer_payload_too_large"


async def test_falsche_content_length_hilft_nicht(raw_origin):
    peer, state = raw_origin
    state["content"] = b"{" + b" " * (peer_outbound.MAX_REPLY_BYTES + 1) + b"}"
    state["stream"] = True
    state["headers"] = {"content-length": "10"}             # lügt
    _req, call = await _ask(peer)
    with pytest.raises((proto.PeerRejected, httpx.HTTPError)) as exc:
        await call
    if isinstance(exc.value, proto.PeerRejected):
        assert exc.value.code == "peer_payload_too_large"


async def test_komprimierte_antwort_abgelehnt(raw_origin):
    peer, state = raw_origin
    state["content"] = b"\x1f\x8b"                            # gzip-Kopf, Inhalt egal
    state["headers"] = {"content-encoding": "gzip"}
    _req, call = await _ask(peer)
    with pytest.raises(proto.PeerRejected) as exc:
        await call
    assert exc.value.code == "peer_payload_invalid"


async def test_anfrage_verlangt_unkomprimierte_antwort(origin):
    peer, state = origin
    req, call = await _ask(peer)
    state["reply"] = _reply(req)
    await call
    assert state["seen"][0].headers["accept-encoding"] == "identity"
