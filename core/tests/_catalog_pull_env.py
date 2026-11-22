"""Gemeinsamer Aufbau für die catalog_pull-Tests (G2/V2).

Eingebunden per ``pytest_plugins = ["tests._catalog_pull_env"]`` (Fixture ``env``).

Dieser Server ist der Hub. Zwei gekoppelte Partner: ``client`` (C, holt ab) und
``origin`` (O, liefert per Push Einträge). Beide nehmen am Katalog teil
(catalog_accept) und melden ``shared``; der Hub selbst hat ``shared`` an.
"""
from __future__ import annotations

import time
import uuid

import pytest

from hydrahive.db.connection import db
from hydrahive.federation import catalog_hub, peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from hydrahive.modules import catalog_sources
from tests._own_rows import only_own_rows
from tests.test_peering_tasks import FakePeer

PULL = "/api/peering/catalog/pull"
PUSH = "/api/peering/catalog/push"
T0 = "2026-11-22T10:00:00Z"
_SEQ: dict[str, int] = {}


def item(item_id, *, kind="task", owner="testuser", updated_at=T0, project_id=None, **over):
    out = {"kind": kind, "item_id": item_id, "owner": owner, "title": f"Titel {item_id}",
           "status": "open" if kind == "task" else "new", "priority": "medium" if kind == "task" else None,
           "project_id": project_id, "project_name": None, "created_at": T0, "updated_at": updated_at}
    out.update(over)
    return out


def next_seq(fp: FakePeer) -> int:
    _SEQ[fp.fp] = _SEQ.get(fp.fp, 0) + 1
    return _SEQ[fp.fp]


def push(client, fp, items=(), deleted=(), *, shared=True, full=None):
    p = {"kind": "catalog_push", "msg_id": str(uuid.uuid4()), "from": "x", "seq": next_seq(fp),
         "interval_seconds": 300, "issued_at": int(time.time()), "items": list(items),
         "deleted": list(deleted), "full_versions": full, "shared": shared, "remote_edits": False}
    r = client.post(PUSH, json=p, headers=fp.headers(p))
    assert r.status_code == 200, r.text
    return r


def pull_payload(fp, *, users=("testuser",), after_rev=0, local_after=None, full=False, limit=500, **over):
    p = {"kind": "catalog_pull", "msg_id": str(uuid.uuid4()), "from": "x", "seq": next_seq(fp),
         "issued_at": int(time.time()), "users": list(users), "after_rev": after_rev,
         "local_after": local_after or {"task": None, "idea": None}, "full": full, "limit": limit}
    p.update(over)
    return p


def pull(client, fp, **kw):
    p = pull_payload(fp, **kw)
    return client.post(PULL, json=p, headers=fp.headers(p)), p


def verified(r, p) -> dict:
    """Antwort mit dem Hub-Schlüssel prüfen (wie es der Client in V3 tut)."""
    assert r.status_code == 200, r.text
    body = r.json()
    hub_peer = {"name": "hub", "public_key": ident.public_key_b64()}
    return proto.verify_reply(hub_peer, r.headers.get(proto.HEADER_SIGNATURE, ""), body,
                              "catalog_items", p["msg_id"])


def code(r) -> str:
    return r.json()["detail"]["code"]


def settings(client, admin_headers, *, shared=True, users=("testuser",), excluded=()):
    body = {"enabled": True, "interval_seconds": 300, "users": list(users),
            "excluded_projects": list(excluded), "shared": shared, "remote_edits": False}
    r = client.put("/api/federation/catalog/settings", headers=admin_headers, json=body)
    assert r.status_code == 200, r.text


def _pair(client, admin_headers, name):
    fp = FakePeer(name)
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": fp.code()}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp.fp})
    r = client.put(f"/api/federation/peers/{peer['id']}/catalog", headers=admin_headers, json={"accept": True})
    assert r.status_code == 200, r.text
    return fp, peer


class FakeSource:
    """Katalog-Quelle des Hubs (eigene Einträge), sortiert nach (updated_at, item_id)."""

    def __init__(self, kind):
        self.kind, self.rows, self.fail = kind, {}, False

    def put(self, item_id, updated_at, owner="testuser", project_id=None):
        self.rows[(owner, item_id)] = item(item_id, kind=self.kind, owner=owner,
                                           updated_at=updated_at, project_id=project_id)

    def list_changed(self, username, after, limit):
        if self.fail:
            raise RuntimeError("Quelle kaputt")
        rows = sorted((r for (o, _), r in self.rows.items() if o == username),
                      key=lambda r: (r["updated_at"], r["item_id"]))
        if after:
            rows = [r for r in rows if (r["updated_at"], r["item_id"]) > tuple(after)]
        return rows[:limit]

    def list_versions(self, username):
        if self.fail:
            raise RuntimeError("Quelle kaputt")
        return [(r["item_id"], r["updated_at"], r["project_id"]) for (o, _), r in self.rows.items() if o == username]

    def get_full(self, username, item_id):
        return self.rows.get((username, item_id))

    def query(self, *a, **kw):
        return []


@pytest.fixture
def env(client, admin_headers):
    for p in client.get("/api/federation/peers", headers=admin_headers).json():
        client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)
    catalog_hub._rate.clear()
    snap = dict(catalog_sources.CATALOG_SOURCES)
    catalog_sources.CATALOG_SOURCES.clear()
    src = {"task": FakeSource("task"), "idea": FakeSource("idea")}
    for k, s in src.items():
        catalog_sources.CATALOG_SOURCES[k] = ("fake", s)
    tables = ("errors_log", "federation_catalog_deletions", "federation_catalog_users",
              "federation_catalog_excluded_projects")
    with only_own_rows(*tables):
        settings(client, admin_headers)
        c_fp, c_peer = _pair(client, admin_headers, "hydrahome")
        o_fp, o_peer = _pair(client, admin_headers, "devbox")
        push(client, c_fp)                      # C meldet shared
        yield {"c": c_fp, "c_peer": c_peer, "o": o_fp, "o_peer": o_peer, "src": src}
        for p in (c_peer, o_peer):
            client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)
        with db() as conn:
            conn.execute("UPDATE federation_catalog_settings SET shared = 0, enabled = 0 WHERE id = 1")
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES.update(snap)
    catalog_hub._rate.clear()
