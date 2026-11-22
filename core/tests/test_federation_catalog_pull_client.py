"""G2/V6 — Client holt beim Hub ab (docs/specs/federation-shared-tasks.md
§Nachricht catalog_pull, §Wann wird abgeholt, §Schalter „Der Client leert seine Kopie“).

Gegen die echte Hub-Route; Aufbau siehe tests/_catalog_pull_client_env.py.
"""
from __future__ import annotations

from hydrahive.db import federation_catalog_mirror as mirror_db
from hydrahive.db.connection import db
from hydrahive.federation import catalog_pull_client as pc
from hydrahive.federation import catalog_sync
from tests._catalog_pull_client_env import mirror_ids, mirror_rows
from tests._catalog_pull_env import item, push, settings

pytest_plugins = ["tests._catalog_pull_env", "tests._catalog_pull_client_env"]


async def test_holt_eintraege_von_o_in_die_kopie(client, cs):
    push(client, cs["o"], [item("o-1", project_name="Hydrahive DEV")])
    assert await pc.pull(full=False) == "ok"
    (row,) = mirror_rows().values()
    assert row["item_id"] == "o-1" and row["origin_name"] == "devbox" and row["project_name"] == "Hydrahive DEV"
    rev, _ = mirror_db.state()
    assert rev > 0
    call = cs["state"]["calls"][-1]
    assert call["kind"] == "catalog_pull" and call["users"] == ["testuser"]


async def test_inkrementell_ab_pull_rev_und_loeschungen(client, cs):
    push(client, cs["o"], [item("o-1"), item("o-2")])
    await pc.pull(full=False)
    rev1, _ = mirror_db.state()
    push(client, cs["o"], deleted=[{"kind": "task", "item_id": "o-1"}])
    assert await pc.pull(full=False) == "ok"
    assert cs["state"]["calls"][-1]["after_rev"] == rev1
    assert mirror_ids() == ["o-2"]


async def test_upsert_nur_wenn_neuer_und_nur_je_art(client, cs):
    push(client, cs["o"], [item("x-1", updated_at="2026-11-22T12:00:00Z", title="neu")])
    await pc.pull(full=False)
    rev, local = mirror_db.state()
    mirror_db.apply_page([{**item("x-1", updated_at="2026-11-22T11:00:00Z", title="alt"),
                           "origin_fp": cs["o"].fp, "origin_name": "devbox"}], [], rev, local, "jetzt")
    assert mirror_rows()[(cs["o"].fp, "task", "x-1")]["title"] == "neu"        # nicht überschrieben
    mirror_db.apply_page([{**item("x-1", kind="idea", updated_at="2026-11-01T00:00:00Z"),
                           "origin_fp": cs["o"].fp, "origin_name": "devbox"}], [], rev, local, "jetzt")
    assert (cs["o"].fp, "idea", "x-1") in mirror_rows()                        # andere Art, eigener Eintrag


async def test_seq_derselbe_zaehler_wie_push_mit_replay_korrektur(client, cs):
    with db() as conn:                                   # Client-Zähler hinter dem Stand am Hub
        conn.execute("UPDATE federation_catalog_settings SET seq = 0 WHERE id = 1")
    assert await pc.pull(full=False) == "ok"             # peer_replay → last_seq + 1 → ok
    seqs = [c["seq"] for c in cs["state"]["calls"]]
    assert len(seqs) == 2 and seqs[1] > seqs[0]


async def test_blaettert_mit_more(client, cs, monkeypatch):
    from hydrahive.federation import catalog_pull as hub_pull
    monkeypatch.setattr(hub_pull, "MAX_LIMIT", 2)
    push(client, cs["o"], [item(f"o-{n}") for n in range(5)])
    pauses = []

    async def record(seconds):
        pauses.append(seconds)
    monkeypatch.setattr(pc, "_pause", record)
    monkeypatch.setattr(pc, "GAP_SECONDS", 2.0)
    assert await pc.pull(full=False) == "ok"
    assert mirror_ids() == [f"o-{n}" for n in range(5)]
    assert len(cs["state"]["calls"]) == 3 and pauses == [2.0, 2.0]   # ≥ 2 s zwischen Seiten


async def test_abbruch_mitten_im_blaettern_behaelt_den_stand_der_fertigen_seiten(client, cs, monkeypatch):
    from hydrahive.federation import catalog_pull as hub_pull
    monkeypatch.setattr(hub_pull, "MAX_LIMIT", 2)
    push(client, cs["o"], [item(f"o-{n}") for n in range(5)])
    cs["state"]["fail_on"] = 2
    assert await pc.pull(full=False) == "hub_unreachable"
    rev, _ = mirror_db.state()
    assert len(mirror_ids()) == 2 and rev > 0                        # erste Seite samt Stand übernommen
    cs["state"]["fail_on"] = None
    assert await pc.pull(full=False) == "ok" and len(mirror_ids()) == 5


async def test_manipulierte_antwort_wird_nicht_uebernommen(client, cs):
    push(client, cs["o"], [item("o-1")])
    cs["state"]["tamper"] = True
    assert await pc.pull(full=False) == "peer_signature_invalid"
    assert mirror_ids() == [] and mirror_db.state()[0] == cs["base"]       # Stand unverändert


async def test_eigene_eintraege_des_hubs_und_reset_local(client, cs):
    cs["src"]["task"].put("h-1", "2026-11-22T09:00:00Z")
    await pc.pull(full=False)
    _, local = mirror_db.state()
    assert "h-1" in mirror_ids() and local["task"][0] == "2026-11-22T09:00:00Z"
    with db() as conn:
        conn.execute("UPDATE federation_catalog_sources SET reset_local = 1 WHERE peer_id = ?", (cs["c_peer"]["id"],))
    await pc.pull(full=False)
    assert mirror_db.state()[1]["task"] is None                       # Cursor für Hub-Einträge von vorn
    await pc.pull(full=False)
    assert cs["state"]["calls"][-1]["local_after"]["task"] is None
    assert mirror_db.state()[1]["task"] is not None


async def test_voller_abgleich_loescht_fehlendes_erst_nach_allen_seiten(client, cs, monkeypatch):
    from hydrahive.federation import catalog_pull as hub_pull
    push(client, cs["o"], [item(f"o-{n}") for n in range(4)])
    await pc.pull(full=False)
    rev, local = mirror_db.state()
    mirror_db.apply_page([{**item("geist"), "origin_fp": cs["o"].fp, "origin_name": "devbox"}], [], rev, local, "j")
    monkeypatch.setattr(hub_pull, "MAX_KEYS", 2)
    cs["state"]["fail_on"] = len(cs["state"]["calls"]) + 2            # zweite Schlüsselseite scheitert
    assert await pc.pull(full=True) == "hub_unreachable"
    assert "geist" in mirror_ids()                                    # abgebrochen: nichts gelöscht
    cs["state"]["fail_on"] = None
    assert await pc.pull(full=True) == "ok"
    assert mirror_ids() == [f"o-{n}" for n in range(4)]
    assert any(c.get("keys_after") for c in cs["state"]["calls"])
    assert mirror_db.last_full_pull_at()


async def test_stuendlich_voll(client, cs):
    assert await pc.pull() == "ok" and cs["state"]["calls"][-1]["full"] is True    # noch nie voll
    assert await pc.pull() == "ok" and cs["state"]["calls"][-1]["full"] is False   # gerade eben
    assert pc.full_due("2026-01-01T00:00:00Z") is True and pc.full_due(None) is True


async def test_not_shared_leert_die_kopie(client, admin_headers, cs):
    push(client, cs["o"], [item("o-1")])
    await pc.pull(full=False)
    push(client, cs["c"], shared=False)                               # Hub sieht C ohne shared
    assert await pc.pull(full=False) == "peer_catalog_not_shared"
    assert mirror_ids() == [] and mirror_db.state()[0] == 0


async def test_not_accepted_leert_die_kopie(client, admin_headers, cs):
    push(client, cs["o"], [item("o-1")])
    await pc.pull(full=False)
    client.put(f"/api/federation/peers/{cs['c_peer']['id']}/catalog", headers=admin_headers, json={"accept": False})
    assert await pc.pull(full=False) == "peer_catalog_not_accepted"
    assert mirror_ids() == []


async def test_nutzerauswahl_und_shared_aus_leeren_die_kopie(client, admin_headers, cs):
    push(client, cs["o"], [item("o-1")])
    await pc.pull(full=False)
    settings(client, admin_headers, users=("testuser", "admin"))
    assert mirror_ids() == [] and mirror_db.state()[0] == 0
    await pc.pull(full=False)
    assert mirror_ids() == ["o-1"]
    settings(client, admin_headers, users=("testuser", "admin"), shared=False)
    assert mirror_ids() == []


async def test_hub_wechsel_leert_die_kopie(client, cs):
    push(client, cs["o"], [item("o-1")])
    await pc.pull(full=False)
    from hydrahive.db import federation_catalog as catalog_db
    catalog_db.set_hub("hub-self-test", False)
    assert mirror_ids() == [] and mirror_db.state()[0] == 0


async def test_ohne_shared_oder_ohne_hub_kein_netzverkehr(client, admin_headers, cs):
    with db() as conn:
        conn.execute("UPDATE federation_catalog_settings SET shared = 0 WHERE id = 1")
    assert await pc.pull() == "inactive"
    with db() as conn:
        conn.execute("UPDATE federation_catalog_settings SET shared = 1, enabled = 0 WHERE id = 1")
    assert await pc.pull() == "inactive"
    with db() as conn:
        conn.execute("UPDATE federation_catalog_settings SET enabled = 1 WHERE id = 1")
        conn.execute("UPDATE federation_peers SET is_hub = 0 WHERE id = 'hub-self-test'")
    assert await pc.pull() == "inactive"
    assert cs["state"]["calls"] == []


async def test_timer_lauf_holt_ab_unter_derselben_sperre(client, cs, monkeypatch):
    from hydrahive.federation import catalog_runner
    order = []

    async def fake_sync(**kw):
        order.append(("push", catalog_sync._lock().locked()))
        return "ok"
    monkeypatch.setattr(catalog_sync, "sync", fake_sync)
    real = pc.pull

    async def spy(**kw):
        order.append(("pull", catalog_sync._lock().locked()))
        return await real(**kw)
    monkeypatch.setattr(pc, "pull", spy)
    push(client, cs["o"], [item("o-1")])
    assert await catalog_runner.timer_tick(1) == "ok"
    assert [o[0] for o in order] == ["push", "pull"] and mirror_ids() == ["o-1"]
