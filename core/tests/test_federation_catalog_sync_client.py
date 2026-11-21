"""S4 — Versand-Motor des Katalog-Clients (docs/specs/federation-catalog.md §Ablauf 2 + 3).

Gegen einen gefälschten Hub (``send_signed`` gemockt, dahinter die echte
Hub-Annahme aus S1). Akzeptanzkriterien 4 (Hub offline → nächster Lauf holt
nach), 5 (gelöschter Task verschwindet per Event oder Abgleich), 8a (Idee + Task
in derselben Sekunde, zwei Änderungen desselben Tasks in derselben Sekunde).
"""
from __future__ import annotations

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.federation import catalog_sync
from tests._catalog_fakes import hub_rows
from tests._catalog_sync_env import I0, T0, T1

pytest_plugins = ["tests._catalog_sync_env"]  # Fixture `env`


def _status() -> dict:
    from hydrahive.db.federation_catalog import get_settings
    return get_settings()


# --- AK 8a: gleiche Sekunde ----------------------------------------------------

async def test_ak8a_idee_und_task_gleiche_sekunde_und_zweite_aenderung(env):
    env["tasks"].put("t-1", T0, title="erste Fassung")
    assert await catalog_sync.sync() == "ok"
    assert client_db.get_cursors()[("testuser", "task")] == T0
    # Zweite Änderung desselben Tasks in derselben Sekunde + Idee mit gleicher Sekunde
    env["tasks"].put("t-1", T0, title="zweite Fassung")
    env["ideas"].put("i-1", "2026-11-21T10:00:00.000000Z")
    env["tasks"].put("t-2", T0)
    assert await catalog_sync.sync() == "ok"
    rows = hub_rows(env["peer"]["id"])
    assert rows[("task", "t-1")]["title"] == "zweite Fassung"
    assert {("task", "t-2"), ("idea", "i-1")} <= set(rows)
    # >= : der zweite Lauf hat beim Cursor T0 begonnen (einschließlich)
    after = [c[2] for c in env["tasks"].calls if c[0] == "list_changed"][-1]
    assert after == (T0, "")


async def test_cursor_je_art_nie_ueber_arten_verglichen(env):
    env["tasks"].put("t-1", T1)
    env["ideas"].put("i-1", I0)   # als String "kleiner" als T0, aber andere Art
    assert await catalog_sync.sync() == "ok"
    cursors = client_db.get_cursors()
    assert cursors[("testuser", "task")] == T1 and cursors[("testuser", "idea")] == I0
    env["ideas"].put("i-2", I0)
    await catalog_sync.sync()
    assert ("idea", "i-2") in hub_rows(env["peer"]["id"])


# --- Keyset, ≤ 500 je Nachricht, Abstand, Cursor erst nach vollständigem Ack -------

async def test_keyset_mehr_als_500_gleiche_zeit_und_cursor_erst_nach_ack(env):
    for i in range(1201):
        env["tasks"].put(f"t-{i:04d}", T0)
    env["hub"].fail_at = 2               # zweite Nachricht geht verloren
    assert await catalog_sync.sync() == "hub_unreachable"
    assert ("testuser", "task") not in client_db.get_cursors()   # Cursor bleibt stehen
    assert _status()["last_error"] == "hub_unreachable"
    env["hub"].fail_at = None
    env["hub"].sent.clear()
    env["pauses"].clear()
    assert await catalog_sync.sync() == "ok"
    sizes = [len(p["items"]) for p in env["hub"].sent]
    assert sizes == [500, 500, 201]
    assert env["pauses"] == [catalog_sync.GAP_SECONDS] * 2 and catalog_sync.GAP_SECONDS >= 2
    assert len([k for k in hub_rows(env["peer"]["id"]) if k[0] == "task"]) == 1201
    assert client_db.get_cursors()[("testuser", "task")] == T0
    seqs = [p["seq"] for p in env["hub"].sent]
    assert seqs == sorted(seqs) and len(set(seqs)) == 3


# --- AK 4: Hub offline → nächster Lauf holt nach ------------------------------

async def test_ak4_hub_offline_naechster_lauf_holt_nach(env):
    env["hub"].offline = True
    env["tasks"].put("t-1", T0)
    assert await catalog_sync.sync(pairs={("testuser", "task")}, heartbeat=False, reason="event") == "hub_unreachable"
    assert hub_rows(env["peer"]["id"]) == {}
    assert _status()["last_error"] == "hub_unreachable" and _status()["last_push_at"]
    env["hub"].offline = False
    assert await catalog_sync.sync() == "ok"   # Timer-Lauf
    assert ("task", "t-1") in hub_rows(env["peer"]["id"])
    st = _status()
    assert st["last_error"] is None and st["last_ok_at"]


# --- AK 5: Löschung per Event und per Abgleich -----------------------------------

async def test_ak5_geloeschter_task_per_event(env, client, admin_headers):
    """Ohne ausgeschlossene Projekte sofort als deleted (mit: siehe test_federation_catalog_review737)."""
    from tests.test_federation_catalog_e1 import _settings_body
    client.put("/api/federation/catalog/settings", headers=admin_headers, json=_settings_body(excluded_projects=[]))
    env["tasks"].put("t-1", T0)
    env["tasks"].put("t-2", T0)
    await catalog_sync.sync()
    del env["tasks"].rows["t-1"]
    result = await catalog_sync.sync(pairs={("testuser", "task")}, entries=[("task", "testuser", "t-1")],
                                     heartbeat=False, reason="event")
    assert result == "ok"
    assert env["hub"].sent[-1]["deleted"] == [{"kind": "task", "item_id": "t-1"}]
    assert set(hub_rows(env["peer"]["id"])) == {("task", "t-2")}


async def test_ak5_geloeschter_task_per_abgleich(env):
    env["tasks"].put("t-1", T0)
    env["tasks"].put("t-2", T0)
    env["ideas"].put("i-1", I0)
    await catalog_sync.sync()
    del env["tasks"].rows["t-1"]          # ohne Event
    assert await catalog_sync.sync(full=True) == "ok"
    assert set(hub_rows(env["peer"]["id"])) == {("task", "t-2"), ("idea", "i-1")}
    assert env["hub"].sent[-1]["full_versions"] is not None
    assert _status()["last_full_at"]


async def test_abgleich_und_push_ohne_ausgeschlossene_projekte(env):
    env["tasks"].put("t-ok", T0)
    env["tasks"].put("t-geheim", T0, project_id="proj-geheim")
    await catalog_sync.sync(full=True)
    sent = env["hub"].sent
    assert [i["item_id"] for p in sent for i in p["items"]] == ["t-ok"]
    assert sent[-1]["full_versions"]["testuser"]["task"] == [["t-ok", T0]]
    assert set(hub_rows(env["peer"]["id"])) == {("task", "t-ok")}
    # Eintrag wandert in ein ausgeschlossenes Projekt → per Event-Abgleich entfernt, ohne seine ID
    env["hub"].sent.clear()
    env["tasks"].put("t-ok", T1, project_id="proj-geheim")
    await catalog_sync.sync(pairs={("testuser", "task")}, entries=[("task", "testuser", "t-ok")], heartbeat=False)
    assert hub_rows(env["peer"]["id"]) == {}
    assert "t-geheim" not in str(env["hub"].sent) and "t-ok" not in str(env["hub"].sent)


async def test_abgleich_bei_kaputter_quelle_schickt_keine_liste(env):
    env["tasks"].put("t-1", T0)
    await catalog_sync.sync()
    env["ideas"].broken = True
    assert await catalog_sync.sync(full=True) == "ok"
    assert env["hub"].sent[-1]["full_versions"] is None      # sonst löschte der Hub alles
    assert ("task", "t-1") in hub_rows(env["peer"]["id"])
    assert "source_failed:idea" in _status()["last_error"]


# --- resync, peer_replay, Ack -----------------------------------------------------

async def test_resync_setzt_cursor_zurueck(env):
    env["tasks"].put("t-1", T0)
    await catalog_sync.sync()
    from hydrahive.db.connection import db
    with db() as conn:   # Hub verliert den Eintrag
        conn.execute("DELETE FROM federation_catalog_items WHERE peer_id = ?", (env["peer"]["id"],))
    env["tasks"].put("t-0", "2026-11-21T09:00:00Z")   # älter als der Cursor → nur per resync
    assert await catalog_sync.sync(pairs=set(), full=True) == "ok"
    assert ("testuser", "task") not in client_db.get_cursors()
    await catalog_sync.sync()
    assert {("task", "t-0"), ("task", "t-1")} <= set(hub_rows(env["peer"]["id"]))


async def test_peer_replay_springt_auf_last_seq_plus_1(env):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO federation_catalog_sources (peer_id, last_seq) VALUES (?, ?) "
                     "ON CONFLICT (peer_id) DO UPDATE SET last_seq = excluded.last_seq",
                     (env["peer"]["id"], client_db.next_seq() + 1000))
    env["tasks"].put("t-1", T0)
    assert await catalog_sync.sync() == "ok"
    rejected, accepted = env["hub"].sent[-2:]
    assert accepted["seq"] > rejected["seq"] and accepted["seq"] >= 1001
    assert ("task", "t-1") in hub_rows(env["peer"]["id"])


async def test_falsches_ack_ist_fehler_cursor_bleibt(env):
    env["hub"].bad_ack = True
    env["tasks"].put("t-1", T0)
    assert await catalog_sync.sync() == "hub_bad_ack"
    assert ("testuser", "task") not in client_db.get_cursors()


async def test_hub_nimmt_nicht_an_grund_im_status(env, client, admin_headers):
    env["hub"].peer["catalog_accept"] = 0
    assert await catalog_sync.sync() == "peer_catalog_not_accepted"
    assert _status()["last_error"] == "peer_catalog_not_accepted"
