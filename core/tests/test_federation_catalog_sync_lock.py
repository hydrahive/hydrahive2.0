"""S4 — Versand-Motor: kein Netz ohne Hub/Sync, gemeinsame Sperre, Abgleich fällig,
Nachrichtenaufteilung (docs/specs/federation-catalog.md §Ablauf 2). Fixture ``env``
aus test_federation_catalog_sync_client.py (gefälschter Hub, echte Hub-Annahme).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from hydrahive.federation import catalog_plan, catalog_sync
from tests.test_federation_catalog_e1 import _settings_body
from tests._catalog_sync_env import T0

pytest_plugins = ["tests._catalog_sync_env"]  # Fixture `env`


async def test_ohne_hub_oder_sync_aus_kein_netzverkehr(env, client, admin_headers):
    client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(enabled=False))
    env["tasks"].put("t-1", T0)
    assert await catalog_sync.sync() == "inactive"
    client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body())
    client.put(f"/api/federation/peers/{env['peer']['id']}/hub", headers=admin_headers, json={"is_hub": False})
    assert await catalog_sync.sync(full=True) == "inactive"
    assert env["hub"].sent == []


async def test_gemeinsame_sperre_nachrichten_nacheinander(env):
    env["hub"].delay = 0.05
    env["tasks"].put("t-1", T0)
    results = await asyncio.gather(*(catalog_sync.sync() for _ in range(3)))
    assert results == ["ok", "ok", "ok"]
    assert env["hub"].max_active == 1
    seqs = [p["seq"] for p in env["hub"].sent]
    assert seqs == sorted(seqs)


async def test_event_lauf_ohne_aenderung_sendet_nichts(env):
    assert await catalog_sync.sync(pairs={("testuser", "task")}, heartbeat=False, reason="event") == "ok"
    assert env["hub"].sent == []
    assert await catalog_sync.sync() == "ok"           # Timer: leeres Lebenszeichen
    assert len(env["hub"].sent) == 1 and env["hub"].sent[0]["items"] == []


def test_full_due():
    now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    assert catalog_sync.full_due(None, 1, now)
    assert catalog_sync.full_due("2026-11-21T10:59:00.000+00:00", 1, now)
    assert not catalog_sync.full_due("2026-11-21T11:30:00.000+00:00", 1, now)
    assert catalog_sync.full_due("2026-11-21T11:30:00.000+00:00", 12, now)
    assert catalog_sync.full_due("kaputt", 1, now)


def test_messages_hoechstens_500_und_abgleich_am_ende():
    plan = catalog_plan.Plan(items=[{"i": n} for n in range(1001)], deleted=[{"d": 1}], full_versions={"u": {}})
    msgs = catalog_plan.messages(plan, heartbeat=False)
    assert [len(m[0]) for m in msgs] == [500, 500, 1]
    assert msgs[0][1] == [{"d": 1}] and msgs[-1][2] == {"u": {}} and msgs[0][2] is None
    assert catalog_plan.messages(catalog_plan.Plan(), heartbeat=False) == []
