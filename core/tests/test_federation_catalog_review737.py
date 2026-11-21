"""Nachbesserungen aus dem Review von PR #737 (Föderations-Katalog Etappe 3).

M1: Fehlt einer Art die Quelle, löscht der Abgleich ihre Einträge am Hub nicht.
M2: IDs aus ausgeschlossenen Projekten verlassen den Server nie, auch nicht als
    ``deleted`` beim Event-Push (Spec §Ablauf 2).
M3: Die Hub-Route macht die DB-Arbeit außerhalb des Event-Loops.
L4: Auswahl-/Hub-Änderung → der nächste Timer-Lauf ist ein Abgleich.
"""
from __future__ import annotations

import asyncio

from hydrahive.federation import catalog_hub, catalog_runner, catalog_sync
from hydrahive.modules import catalog_sources
from tests._catalog_fakes import hub_rows
from tests._catalog_sync_env import I0, T0, T1
from tests.test_federation_catalog_push_hub import URL, _item, _push, _send

pytest_plugins = ["tests._catalog_sync_env", "tests.test_federation_catalog_push_hub"]  # env, hub


# --- M1 ---------------------------------------------------------------------------

async def test_m1_fehlende_quelle_loescht_am_hub_nichts(env):
    env["tasks"].put("t-1", T0)
    env["ideas"].put("i-1", I0)
    await catalog_sync.sync()
    assert {("task", "t-1"), ("idea", "i-1")} <= set(hub_rows(env["peer"]["id"]))
    del catalog_sources.CATALOG_SOURCES["idea"]          # scratchpad lädt nach Update nicht
    assert await catalog_sync.sync(full=True) == "ok"
    assert "idea" not in env["hub"].sent[-1]["full_versions"]["testuser"]
    assert {("task", "t-1"), ("idea", "i-1")} <= set(hub_rows(env["peer"]["id"]))


async def test_m1_gelistete_art_ohne_nutzer_gilt_als_leer(env):
    """Abgewählter Nutzer: innerhalb einer gelisteten Art wird er weiter entfernt."""
    env["tasks"].put("t-1", T0)
    env["tasks"].put("t-anna", T0, owner="anna")
    await catalog_sync.sync()
    from hydrahive.db.connection import db
    with db() as conn:   # Hub hat noch einen Eintrag eines Nutzers, der nicht mehr gewählt ist
        conn.execute("INSERT INTO federation_catalog_items (peer_id, kind, item_id, owner, title, status, "
                     "updated_at, received_at) VALUES (?, 'task', 't-alt', 'anna', 'T', 'open', ?, 'now')",
                     (env["peer"]["id"], T0))
    await catalog_sync.sync(full=True)
    assert ("task", "t-alt") not in hub_rows(env["peer"]["id"])


# --- M2 ---------------------------------------------------------------------------

async def test_m2_bearbeiten_im_ausgeschlossenen_projekt_schickt_keine_id(env):
    env["tasks"].put("t-geheim", T0, project_id="proj-geheim")
    env["tasks"].put("t-ok", T0)
    await catalog_sync.sync()
    env["tasks"].put("t-geheim", T1, project_id="proj-geheim", title="Befund")
    await catalog_sync.sync(pairs={("testuser", "task")}, entries=[("task", "testuser", "t-geheim")],
                            heartbeat=False, reason="event")
    assert "t-geheim" not in str(env["hub"].sent)
    assert all(p["deleted"] == [] for p in env["hub"].sent)


async def test_m2_loeschen_bei_ausgeschlossenen_projekten_per_abgleich_sofort(env):
    env["tasks"].put("t-1", T0)
    env["tasks"].put("t-2", T0)
    await catalog_sync.sync()
    del env["tasks"].rows["t-1"]
    await catalog_sync.sync(pairs={("testuser", "task")}, entries=[("task", "testuser", "t-1")],
                            heartbeat=False, reason="event")
    last = env["hub"].sent[-1]
    assert last["deleted"] == [] and last["full_versions"] is not None   # keine ID, aber Abgleich
    assert set(hub_rows(env["peer"]["id"])) == {("task", "t-2")}


async def test_m2_verschieben_ins_ausgeschlossene_projekt_entfernt_ohne_id(env):
    env["tasks"].put("t-1", T0)
    await catalog_sync.sync()
    env["hub"].sent.clear()
    env["tasks"].put("t-1", T1, project_id="proj-geheim")
    await catalog_sync.sync(pairs={("testuser", "task")}, entries=[("task", "testuser", "t-1")],
                            heartbeat=False, reason="event")
    assert hub_rows(env["peer"]["id"]) == {}
    assert "t-1" not in str(env["hub"].sent)


async def test_m2_ohne_ausgeschlossene_projekte_weiter_sofort_deleted(env, client, admin_headers):
    from tests.test_federation_catalog_e1 import _settings_body
    client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(excluded_projects=[]))
    env["tasks"].put("t-1", T0)
    await catalog_sync.sync()
    del env["tasks"].rows["t-1"]
    await catalog_sync.sync(pairs={("testuser", "task")}, entries=[("task", "testuser", "t-1")],
                            heartbeat=False, reason="event")
    assert env["hub"].sent[-1]["deleted"] == [{"kind": "task", "item_id": "t-1"}]
    assert env["hub"].sent[-1]["full_versions"] is None


# --- M3 ---------------------------------------------------------------------------

def test_m3_hub_route_arbeitet_ausserhalb_des_event_loops(client, hub, monkeypatch):
    fp, _ = hub
    seen: list[bool] = []
    real = catalog_hub.accept_push

    def spy(peer, payload):
        try:
            asyncio.get_running_loop()
            seen.append(True)       # liefe im Event-Loop
        except RuntimeError:
            seen.append(False)      # Worker-Thread
        return real(peer, payload)
    monkeypatch.setattr(catalog_hub, "accept_push", spy)
    r = _send(client, fp, _push(1, [_item()]))
    assert r.status_code == 200 and seen == [False]
    assert URL == "/api/peering/catalog/push"


def test_m3_audit_kuerzt_langen_absender(client, hub):
    payload = _push(1)
    r = client.post(URL, json=payload, headers={"X-HH-Peer": "x" * 5000, "X-HH-Signature": "y"})
    assert r.status_code == 403
    from hydrahive.db.connection import db
    with db() as conn:
        msgs = [m[0] for m in conn.execute(
            "SELECT error_message FROM errors_log WHERE source = 'federation.catalog'").fetchall()]
    assert msgs and all(len(m) < 400 for m in msgs)


# --- L4 ---------------------------------------------------------------------------

async def test_l4_auswahl_geaendert_naechster_timer_ist_abgleich(env, client, admin_headers):
    from tests.test_federation_catalog_e1 import _settings_body
    env["tasks"].put("t-1", T0)
    await catalog_sync.sync(full=True)
    assert await catalog_runner.timer_tick(2) == "ok"
    assert env["hub"].sent[-1]["full_versions"] is None          # gerade abgeglichen
    client.put("/api/federation/catalog/settings", headers=admin_headers,
               json=_settings_body(excluded_projects=["proj-geheim", "proj-neu"]))
    assert await catalog_runner.timer_tick(3) == "ok"
    assert env["hub"].sent[-1]["full_versions"] is not None      # Auswahl geändert → Abgleich
