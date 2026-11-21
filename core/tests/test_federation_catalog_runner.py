"""S5 — Einbindung des Katalog-Clients (docs/specs/federation-catalog.md §Ablauf 2).

Timer- und Event-Loop mit verkürzten Zeiten gegen den gefälschten Hub
(``send_signed`` gemockt, dahinter die echte Hub-Annahme aus S1).
Akzeptanzkriterien 2 (Client-Seite: ohne enabled/Nutzer/Hub-Annahme kommt nichts
an, Grund im Status), 3 (Event ≤ 15 s), 13 (Katalog aus → kein Netzverkehr),
dazu Shutdown ohne hängende Tasks und „Jetzt abgleichen“.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from hydrahive.federation import catalog_changes, catalog_runner, catalog_sync
from hydrahive.modules.context import ModuleContext
from tests._catalog_fakes import hub_rows
from tests._catalog_sync_env import T0
from tests.test_federation_catalog_e1 import _settings_body

pytest_plugins = ["tests._catalog_sync_env"]  # Fixture `env`


@pytest.fixture
def fast(env, monkeypatch):
    """Verkürzte Zeiten: Bündelung 0,2 s statt 10 s, erster Timer-Lauf sofort."""
    monkeypatch.setattr(catalog_runner, "POLL", 0.02)
    monkeypatch.setattr(catalog_runner, "BUNDLE", 0.2)
    monkeypatch.setattr(catalog_runner, "FIRST_DELAY", 0.0)
    catalog_changes.refresh_gate()
    yield env
    catalog_changes._reset_for_tests()


async def _until(check, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return True
        await asyncio.sleep(0.02)
    return False


async def _stop(stop, tasks):
    stop.set()
    done, pending = await asyncio.wait(tasks, timeout=2.0)
    assert not pending, "Loop hängt nach Stop"
    for t in done:
        assert t.exception() is None


# --- AK 3: Event-Push -----------------------------------------------------------

async def test_ak3_neue_idee_per_event_mit_buendelung(fast):
    env = fast
    stop = asyncio.Event()
    task = asyncio.create_task(catalog_runner.run_events(stop))
    started = time.monotonic()
    ctx = ModuleContext("scratchpad")
    for i in range(5):                       # fünf Änderungen kurz hintereinander
        env["ideas"].put(f"i-{i}", f"2026-11-21T10:00:0{i}.000000Z")
        ctx.catalog_changed("idea", "testuser", f"i-{i}")
    assert await _until(lambda: len(hub_rows(env["peer"]["id"])) == 5)
    elapsed = time.monotonic() - started
    await _stop(stop, [task])
    assert len(env["hub"].sent) == 1                       # gebündelt: eine Nachricht
    assert env["hub"].sent[0]["full_versions"] is None
    assert catalog_runner.BUNDLE <= elapsed < catalog_runner.BUNDLE + 2.0
    assert catalog_runner.BUNDLE + catalog_runner.POLL < 15   # echte Werte: 10 s + 1 s ≤ 15 s


def test_ak3_echte_zeiten_bleiben_unter_15_s():
    assert catalog_runner.BUNDLE == 10.0 and catalog_runner.POLL == 1.0
    assert catalog_runner.BUNDLE + catalog_runner.POLL < 15


async def test_event_loeschung_geht_sofort_als_deleted(fast):
    env = fast
    env["tasks"].put("t-1", T0)
    await catalog_sync.sync()
    del env["tasks"].rows["t-1"]
    ModuleContext("tasks").catalog_changed("task", "testuser", "t-1")
    assert await catalog_runner.event_tick() == "ok"
    assert env["hub"].sent[-1]["deleted"] == [{"kind": "task", "item_id": "t-1"}]
    assert hub_rows(env["peer"]["id"]) == {}


async def test_overflow_startet_vollen_lauf(fast, monkeypatch):
    env = fast
    monkeypatch.setattr(catalog_changes, "MAX_PENDING", 1)
    env["tasks"].put("t-1", T0)
    env["tasks"].put("t-2", T0)
    ctx = ModuleContext("tasks")
    ctx.catalog_changed("task", "testuser", "t-1")
    ctx.catalog_changed("task", "testuser", "t-2")      # → overflow
    assert await catalog_runner.event_tick() == "ok"
    assert {("task", "t-1"), ("task", "t-2")} <= set(hub_rows(env["peer"]["id"]))
    assert not catalog_changes.is_dirty()


async def test_event_ohne_vormerkung_sendet_nichts(fast):
    assert await catalog_runner.event_tick() is None
    assert fast["hub"].sent == []


async def test_event_fehlschlag_keine_wiederholung(fast):
    env = fast
    env["hub"].offline = True
    env["tasks"].put("t-1", T0)
    ModuleContext("tasks").catalog_changed("task", "testuser", "t-1")
    assert await catalog_runner.event_tick() == "hub_unreachable"
    assert await catalog_runner.event_tick() is None        # nichts mehr vorgemerkt
    assert len(env["hub"].sent) == 1
    env["hub"].offline = False
    assert await catalog_runner.timer_tick(1) == "ok"       # Timer holt nach (AK 4)
    assert ("task", "t-1") in hub_rows(env["peer"]["id"])


# --- Timer -------------------------------------------------------------------------

async def test_timer_erster_lauf_dann_intervall_live(fast, monkeypatch):
    """Intervall wird bei jedem Durchlauf neu gelesen. Deterministisch: die Änderung
    passiert IM zweiten Warten, also genau zwischen zwei Läufen (kein Zeitrennen)."""
    from hydrahive.db import federation_catalog as catalog_db

    env = fast
    waits: list[float] = []
    real_wait = catalog_runner._wait

    async def record_wait(stop, seconds):
        waits.append(seconds)
        if len(waits) == 2:                    # nach Lauf 1: Admin stellt 900 s ein
            catalog_db.update_settings(enabled=True, interval_seconds=900)
        if len(waits) >= 3:
            stop.set()
        return await real_wait(stop, 0)
    monkeypatch.setattr(catalog_runner, "_wait", record_wait)
    stop = asyncio.Event()
    await asyncio.wait_for(catalog_runner.run_timer(stop), timeout=5)
    assert waits == [catalog_runner.FIRST_DELAY, 120, 900]   # Start, altes Intervall, neues Intervall
    assert len(env["hub"].sent) == 2                          # Lebenszeichen je Lauf


async def test_timer_abgleich_wenn_faellig(fast):
    env = fast
    env["tasks"].put("t-1", T0)
    assert await catalog_runner.timer_tick(1) == "ok"          # last_full_at leer → Abgleich
    assert env["hub"].sent[-1]["full_versions"] is not None
    assert await catalog_runner.timer_tick(2) == "ok"          # gerade abgeglichen → Delta
    assert env["hub"].sent[-1]["full_versions"] is None


def test_echte_timer_werte():
    assert catalog_runner.FIRST_DELAY == 60.0 and catalog_runner.FALLBACK_INTERVAL == 300


# --- AK 2 (Client) + AK 13: kein Netzverkehr, Grund im Status -------------------------

@pytest.mark.parametrize("over", [{"enabled": False}, {"users": []}])
async def test_ak2_ohne_enabled_oder_nutzer_kein_netzverkehr(fast, client, admin_headers, over):
    env = fast
    client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(**over))
    env["tasks"].put("t-1", T0)
    ModuleContext("tasks").catalog_changed("task", "testuser", "t-1")
    assert not catalog_changes.is_dirty()                      # nichts vorgemerkt
    assert await catalog_runner.timer_tick(1) == "inactive"
    assert await catalog_runner.event_tick() is None
    r = client.post("/api/federation/catalog/sync-now", headers=admin_headers)
    assert r.status_code == 200 and r.json()["result"] == "inactive"
    assert env["hub"].sent == [] and hub_rows(env["peer"]["id"]) == {}


async def test_ak13_ohne_hub_kein_netzverkehr(fast, client, admin_headers):
    env = fast
    client.put(f"/api/federation/peers/{env['peer']['id']}/hub", headers=admin_headers, json={"is_hub": False})
    stop = asyncio.Event()
    tasks = catalog_runner.start(stop)
    ModuleContext("tasks").catalog_changed("task", "testuser", "t-1")
    await asyncio.sleep(0.4)
    await _stop(stop, tasks)
    assert env["hub"].sent == []


async def test_ak2_hub_nimmt_nicht_an_grund_im_status(fast, client, admin_headers):
    env = fast
    env["hub"].peer["catalog_accept"] = 0
    r = client.post("/api/federation/catalog/sync-now", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["result"] == "peer_catalog_not_accepted"
    assert r.json()["settings"]["last_error"] == "peer_catalog_not_accepted"
    assert hub_rows(env["peer"]["id"]) == {}


# --- Jetzt abgleichen + Shutdown -------------------------------------------------------

async def test_sync_now_voller_abgleich_nur_admin(fast, client, admin_headers, auth_headers):
    env = fast
    env["tasks"].put("t-1", T0)
    assert client.post("/api/federation/catalog/sync-now", headers=auth_headers).status_code == 403
    r = client.post("/api/federation/catalog/sync-now", headers=admin_headers)
    assert r.status_code == 200 and r.json()["result"] == "ok"
    assert env["hub"].sent[-1]["full_versions"] is not None
    assert r.json()["settings"]["last_ok_at"] and r.json()["settings"]["last_full_at"]


async def test_shutdown_beendet_beide_loops_sofort(fast, monkeypatch):
    monkeypatch.setattr(catalog_runner, "FIRST_DELAY", 60.0)   # echte Wartezeit
    monkeypatch.setattr(catalog_runner, "POLL", 1.0)
    stop = asyncio.Event()
    tasks = catalog_runner.start(stop)
    await asyncio.sleep(0.05)
    started = time.monotonic()
    await _stop(stop, tasks)
    assert time.monotonic() - started < 1.0
    assert fast["hub"].sent == []


def test_lifespan_startet_und_stoppt_katalog_loops():
    import inspect

    from hydrahive.api import lifespan
    src = inspect.getsource(lifespan)
    assert "catalog_runner.start(catalog_stop)" in src
    assert "catalog_stop.set()" in src and "*catalog_tasks" in src
