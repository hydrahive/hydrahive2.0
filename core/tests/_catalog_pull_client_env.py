"""Aufbau für die Client-Tests des Abholens (G2/V6).

Eingebunden per ``pytest_plugins = ["tests._catalog_pull_env", "tests._catalog_pull_client_env"]``.

Dieselbe Test-DB spielt beide Seiten: Hub (aus ``_catalog_pull_env``: Partner C
und O, eigene Quellen) und Client (Einstellungen, Kopie). Der Client hat eine
Hub-Zeile mit dem eigenen Schlüssel. ``request_signed`` wird so umgelenkt, dass
die Anfrage an die ECHTE Hub-Route geht, signiert mit dem Schlüssel von C, und
die Antwort mit dem echten ``verify_reply`` gegen den Schlüssel der Hub-Zeile
geprüft wird. Das begrenzte Lesen selbst testet test_federation_catalog_reply_sig.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from hydrahive.db import federation_catalog_mirror as mirror_db
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.federation import catalog_pull_client, peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.peer_outbound import ReplyUnavailable

HUB_ID = "hub-self-test"


def mirror_rows() -> dict[tuple[str, str, str], dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM federation_catalog_mirror").fetchall()
    return {(r["origin_fp"], r["kind"], r["item_id"]): dict(r) for r in rows}


def mirror_ids() -> list[str]:
    return sorted(k[2] for k in mirror_rows())


@pytest.fixture
def cs(client, env, monkeypatch):
    pub = ident.public_key_b64()
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at, is_hub) "
            "VALUES (?, 'der-hub', 'https://hub.example', ?, ?, 'active', ?, 1)",
            (HUB_ID, pub, ident.fingerprint(pub), now_iso()),
        )
    mirror_db.clear()
    with db() as conn:   # ab dem aktuellen Stand: Löschzeilen anderer Tests nicht mitholen
        conn.execute("UPDATE federation_catalog_settings SET pull_rev = ? WHERE id = 1", (env["base"],))
    state = {"calls": [], "fail_on": None, "tamper": False}

    async def fake_request(peer, path, payload, *, reply_kind, timeout):
        state["calls"].append(payload)
        assert path == "/api/peering/catalog/pull" and reply_kind == "catalog_items"
        assert peer["id"] == HUB_ID                           # nur der eigene Hub
        if state["fail_on"] == len(state["calls"]):
            raise httpx.ConnectError("Hub weg", request=httpx.Request("POST", peer["url"] + path))
        r = await asyncio.to_thread(client.post, path, json=payload, headers=env["c"].headers(payload))
        if r.status_code == 404:
            raise ReplyUnavailable(peer["name"])
        r.raise_for_status()
        body = r.json()
        if state["tamper"]:
            body["items"] = [{"origin_fp": "x", "kind": "task", "item_id": "untergeschoben", "owner": "testuser"}]
        return proto.verify_reply(peer, r.headers.get(proto.HEADER_SIGNATURE, ""), body, reply_kind,
                                  payload["msg_id"])

    monkeypatch.setattr(catalog_pull_client, "request_signed", fake_request)
    monkeypatch.setattr(catalog_pull_client, "GAP_SECONDS", 0)
    yield {**env, **state, "state": state}
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (HUB_ID,))
    mirror_db.clear()
