"""F1 (Live-Befund 22.11.): Fehlerantworten des Hubs werden über eine ECHTE Stream-Antwort
(httpx.MockTransport) gelesen. Vorher warf ``_error`` ``httpx.ResponseNotRead``, im Cockpit
stand nur ``pull_failed``, und weder ``peer_replay`` → ``last_seq + 1`` noch das Leeren der
Kopie griffen. Der TestClient der übrigen Tests liest Antworten vollständig und bildet das
nicht nach.
"""
from __future__ import annotations

import json

import httpx
import pytest

from hydrahive.db import federation_catalog_mirror as mirror_db
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.federation import catalog_pull_client as pc
from hydrahive.federation import peer_identity as ident
from hydrahive.federation import peer_outbound
from hydrahive.federation import peer_protocol as proto

HUB_ID = "hub-err-test"


class _Chunks(httpx.AsyncByteStream):
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def __aiter__(self):
        for i in range(0, len(self.data), 7):          # kleine Stücke: wirklich gestreamt
            yield self.data[i:i + 7]


@pytest.fixture
def hub(monkeypatch, client):
    pub = ident.public_key_b64()
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (HUB_ID,))
        conn.execute(
            "INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at, is_hub) "
            "VALUES (?, 'err-hub', 'https://err-hub.example', ?, ?, 'active', ?, 1)",
            (HUB_ID, pub, ident.fingerprint(pub), now_iso()),
        )
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute("UPDATE federation_catalog_settings SET enabled = 1, shared = 1 WHERE id = 1")
        conn.execute("INSERT OR IGNORE INTO federation_catalog_users (username) VALUES ('testuser')")
    replies: list[tuple[int, dict]] = []
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append(payload)
        status, body = replies.pop(0) if replies else (500, {})
        if status == 200:
            body = proto.new_catalog_items(payload["msg_id"], {**body, "ack_seq": payload["seq"]})
            return httpx.Response(200, stream=_Chunks(json.dumps(body).encode()),
                                  headers={proto.HEADER_SIGNATURE: ident.sign(body)})
        return httpx.Response(status, stream=_Chunks(json.dumps(body).encode()),
                              headers={"content-type": "application/json"})

    real = httpx.AsyncClient

    def factory(*a, **kw):
        kw.pop("verify", None)
        return real(*a, transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(peer_outbound.httpx, "AsyncClient", factory)
    monkeypatch.setattr(pc, "GAP_SECONDS", 0)
    mirror_db.clear()
    yield replies, seen
    mirror_db.clear()
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (HUB_ID,))
        conn.execute("UPDATE federation_catalog_settings SET enabled = 0, shared = 0 WHERE id = 1")


def _page(**over):
    body = {"items": [], "deleted": [], "next_rev": 5, "local_next": {"task": None, "idea": None},
            "more": False, "full": False, "full_keys": None, "keys_next": None, "reset_local": False,
            "instances": []}
    body.update(over)
    return body


def _fill_mirror():
    item = {"origin_fp": "fp-x", "kind": "task", "item_id": "t-1", "origin_name": "x", "owner": "testuser",
            "title": "T", "status": "open", "priority": None, "project_id": None, "project_name": None,
            "created_at": "2026-11-22T10:00:00Z", "updated_at": "2026-11-22T10:00:00Z"}
    mirror_db.apply_page([item], [], 3, {"task": None, "idea": None}, now_iso())


@pytest.mark.parametrize("code", ["peer_catalog_not_shared", "peer_catalog_not_accepted"])
async def test_ablehnung_kommt_als_code_an_und_leert_die_kopie(hub, code):
    replies, _ = hub
    _fill_mirror()
    replies.append((403, {"detail": {"code": code}}))
    assert await pc.pull(full=False) == code                  # vorher: "pull_failed"
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM federation_catalog_mirror").fetchone()[0] == 0
        row = conn.execute("SELECT last_pull_error FROM federation_catalog_settings WHERE id = 1").fetchone()
    assert row[0] == code and mirror_db.state()[0] == 0


async def test_peer_replay_springt_auf_last_seq_plus_1(hub):
    replies, seen = hub
    with db() as conn:
        target = conn.execute("SELECT seq FROM federation_catalog_settings WHERE id = 1").fetchone()[0] + 500
    replies.append((409, {"detail": {"code": "peer_replay", "params": {"last_seq": target}}}))
    replies.append((200, _page()))
    assert await pc.pull(full=False) == "ok"
    assert seen[1]["seq"] == target + 1                       # zweiter Versuch mit last_seq + 1


async def test_rate_limit_und_unbekannter_fehler(hub):
    replies, _ = hub
    replies.append((429, {"detail": {"code": "peer_rate_limited"}}))
    assert await pc.pull(full=False) == "peer_rate_limited"
    replies.append((502, {"nicht": "erwartet"}))
    assert await pc.pull(full=False) == "http_502"


async def test_riesige_fehlerantwort_wird_nur_begrenzt_gelesen(hub, monkeypatch):
    replies, _ = hub
    monkeypatch.setattr(peer_outbound, "MAX_ERROR_BYTES", 64)
    replies.append((403, {"detail": {"code": "peer_catalog_not_shared"}, "x": "y" * 10_000}))
    assert await pc.pull(full=False) == "http_403"            # abgeschnitten: kein JSON, aber kein Absturz


async def test_request_signed_reicht_lesbaren_statusfehler_weiter(hub):
    replies, _ = hub
    replies.append((403, {"detail": {"code": "peer_catalog_not_shared"}}))
    peer = {"name": "err-hub", "url": "https://err-hub.example", "public_key": ident.public_key_b64()}
    with pytest.raises(httpx.HTTPStatusError) as exc:
        await peer_outbound.request_signed(peer, "/x", proto.new_catalog_pull(1, ["t"], 0, {}),
                                           reply_kind="catalog_items", timeout=5)
    assert exc.value.response.status_code == 403
    assert exc.value.response.json()["detail"]["code"] == "peer_catalog_not_shared"


# --- Übrige Aufrufer (F1: alle prüfen) -------------------------------------------------

async def test_push_liest_fehlercode_aus_stream_antwort(hub, monkeypatch):
    """Push (catalog_sync) nutzt send_signed mit client.post, das die Antwort ganz liest:
    peer_replay mit last_seq kommt an, auch wenn der Hub die Antwort streamt."""
    from hydrahive.federation import catalog_sync, peer_inbound

    replies, seen = hub
    monkeypatch.setattr(peer_inbound.httpx, "AsyncClient", peer_outbound.httpx.AsyncClient)
    with db() as conn:
        target = conn.execute("SELECT seq FROM federation_catalog_settings WHERE id = 1").fetchone()[0] + 500
    replies.append((409, {"detail": {"code": "peer_replay", "params": {"last_seq": target}}}))
    replies.append((403, {"detail": {"code": "peer_catalog_not_accepted"}}))
    peer = {"name": "err-hub", "url": "https://err-hub.example"}
    with pytest.raises(catalog_sync.SyncFailed) as exc:
        await catalog_sync.send_message(peer, 300, [], [], None)
    assert exc.value.code == "peer_catalog_not_accepted"      # Code gelesen, nicht http_403
    assert seen[1]["seq"] == target + 1                       # peer_replay → last_seq + 1


async def test_fetch_zeigt_offline_bei_fehlerantwort(hub):
    """Fetch (catalog_detail) wertet keinen Code aus: jeder HTTP-Fehler → offline. Mit F1 ist
    der Fehler ein lesbarer HTTPStatusError, den catalog_detail bereits abfängt (httpx.HTTPError)."""
    replies, _ = hub
    replies.append((500, {"detail": {"code": "x"}}))
    peer = {"name": "err-hub", "url": "https://err-hub.example", "public_key": ident.public_key_b64()}
    with pytest.raises(httpx.HTTPError):
        await peer_outbound.request_signed(peer, "/api/peering/catalog/fetch",
                                           proto.new_catalog_fetch("task", "t-1", "u"),
                                           reply_kind="catalog_item", timeout=5)
