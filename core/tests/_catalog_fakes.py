"""Hilfen für die Tests des Katalog-Clients (Etappe 3, S4).

- ``FakeSource``: Katalog-Quelle im Speicher mit echtem Keyset-Verhalten.
- ``FakeHub``: ersetzt ``send_signed``. Dahinter steckt die ECHTE Hub-Annahme
  aus S1 (``catalog_hub.accept_push``) auf derselben Test-DB, also Seq-Prüfung,
  Upsert nur bei ``updated_at`` ≥ gespeichert, ``deleted`` und Abgleich.
"""
from __future__ import annotations

import asyncio

import httpx

from hydrahive.federation import catalog_hub
from hydrahive.federation import peer_protocol as proto
from hydrahive.modules.context import CatalogSource


class FakeSource:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.rows: dict[str, dict] = {}
        self.calls: list[tuple] = []
        self.broken = False

    def put(self, item_id: str, updated_at: str, *, owner: str = "testuser", title: str | None = None,
            status: str | None = None, project_id: str | None = None) -> None:
        self.rows[item_id] = {
            "kind": self.kind, "item_id": item_id, "owner": owner, "title": title or f"T {item_id}",
            "status": status or ("open" if self.kind == "task" else "new"),
            "priority": "medium" if self.kind == "task" else None, "project_id": project_id,
            "project_name": None, "created_at": updated_at, "updated_at": updated_at,
        }

    def list_changed(self, username, after, limit):
        self.calls.append(("list_changed", username, after, limit))
        if self.broken:
            raise RuntimeError("Quelle kaputt")
        rows = sorted((r for r in self.rows.values() if r["owner"] == username),
                      key=lambda r: (r["updated_at"], r["item_id"]))
        if after is not None:
            rows = [r for r in rows if (r["updated_at"], r["item_id"]) > tuple(after)]
        return [dict(r) for r in rows[:limit]]

    def list_versions(self, username):
        if self.broken:
            raise RuntimeError("Quelle kaputt")
        return [(r["item_id"], r["updated_at"], r["project_id"])
                for r in self.rows.values() if r["owner"] == username]

    def get_full(self, username, item_id):
        row = self.rows.get(item_id)
        return dict(row, description="x") if row and row["owner"] == username else None

    def query(self, usernames, project, status, q, limit, offset):
        return []

    def as_source(self) -> CatalogSource:
        return CatalogSource(kind=self.kind, list_changed=self.list_changed, list_versions=self.list_versions,
                             get_full=self.get_full, query=self.query)


class FakeHub:
    """``send_signed``-Ersatz. ``fail_at``: Nummer des Aufrufs (1-basiert), der scheitert."""

    def __init__(self, hub_peer: dict) -> None:
        self.peer = {**hub_peer, "catalog_accept": 1}
        self.sent: list[dict] = []
        self.offline = False
        self.fail_at: int | None = None
        self.bad_ack = False
        self.delay = 0.0
        self.active = 0
        self.max_active = 0

    async def __call__(self, peer: dict, path: str, payload: dict) -> httpx.Response:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            request = httpx.Request("POST", peer["url"] + path)
            assert path == "/api/peering/catalog/push"
            self.sent.append(payload)
            if self.offline or (self.fail_at is not None and len(self.sent) == self.fail_at):
                raise httpx.ConnectError("Hub nicht erreichbar", request=request)
            catalog_hub._rate.clear()
            try:
                body = await asyncio.to_thread(catalog_hub.accept_push, self.peer, payload)
            except proto.PeerRejected as exc:
                detail = {"code": exc.code}
                if isinstance(exc, catalog_hub.CatalogReplay):
                    detail["params"] = {"last_seq": exc.last_seq}
                status = 409 if exc.code == "peer_replay" else 403
                response = httpx.Response(status, json={"detail": detail}, request=request)
                raise httpx.HTTPStatusError("abgelehnt", request=request, response=response)
            if self.bad_ack:
                body = {**body, "ack_seq": -1}
            return httpx.Response(200, json=body, request=request)
        finally:
            self.active -= 1


def hub_rows(peer_id: str) -> dict[tuple[str, str], dict]:
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT * FROM federation_catalog_items WHERE peer_id = ?", (peer_id,)).fetchall()
    return {(r["kind"], r["item_id"]): dict(r) for r in rows}
