"""G2/V2 — catalog_pull: Inhalt der Antwort (Bedingungen 2, 4, 5, Löschungen,
eigene Einträge des Hubs, reset_local, instances).
"""
from __future__ import annotations

from hydrahive.db.connection import db
from hydrahive.federation import peer_identity as ident
from tests._catalog_pull_env import item, pull, push, settings, verified

pytest_plugins = ["tests._catalog_pull_env"]  # Fixture `env`


def _ids(body):
    return sorted(i["item_id"] for i in body["items"])


def test_eintrag_von_o_kommt_bei_c_an_mit_herkunft(client, env):
    push(client, env["o"], [item("o-1", project_id="p1", project_name="Hydrahive DEV")])
    body = verified(*pull(client, env["c"]))
    (got,) = body["items"]
    assert got["item_id"] == "o-1" and got["origin_fp"] == env["o"].fp and got["origin_name"] == "devbox"
    assert got["project_name"] == "Hydrahive DEV" and got["title"] == "Titel o-1"
    assert set(got) == {"origin_fp", "origin_name", "kind", "item_id", "owner", "title", "status",
                        "priority", "project_id", "project_name", "created_at", "updated_at"}
    assert body["next_rev"] > 0 and body["more"] is False


def test_nie_eigene_eintraege_zurueck(client, env):
    push(client, env["c"], [item("c-1")])                        # C ist selbst Ursprung
    push(client, env["o"], [item("o-1")])
    assert _ids(verified(*pull(client, env["c"]))) == ["o-1"]
    assert _ids(verified(*pull(client, env["o"]))) == ["c-1"]    # und umgekehrt


def test_nur_nutzer_aus_der_liste_von_c(client, env):
    push(client, env["o"], [item("o-1"), item("o-2", owner="anna")])
    assert _ids(verified(*pull(client, env["c"]))) == ["o-1"]
    assert verified(*pull(client, env["c"], users=[]))["items"] == []


def test_o_ohne_shared_oder_ohne_accept_nicht_sichtbar(client, admin_headers, env):
    push(client, env["o"], [item("o-1")], shared=False)
    assert verified(*pull(client, env["c"]))["items"] == []
    push(client, env["o"], [], shared=True)                      # Wiederkehr: neue rev
    assert _ids(verified(*pull(client, env["c"]))) == ["o-1"]
    client.put(f"/api/federation/peers/{env['o_peer']['id']}/catalog", headers=admin_headers, json={"accept": False})
    body = verified(*pull(client, env["c"]))
    assert body["items"] == [] and body["instances"][1:] == []


def test_wegfall_kommt_als_loeschung_an(client, env):
    push(client, env["o"], [item("o-1")])
    first = verified(*pull(client, env["c"]))
    push(client, env["o"], [], shared=False)                     # O teilt nicht mehr
    body = verified(*pull(client, env["c"], after_rev=first["next_rev"]))
    assert body["deleted"] == [{"origin_fp": env["o"].fp, "kind": "task", "item_id": "o-1"}]
    assert body["next_rev"] > first["next_rev"]


def test_geloeschter_eintrag_und_inkrementell(client, env):
    push(client, env["o"], [item("o-1"), item("o-2")])
    first = verified(*pull(client, env["c"]))
    push(client, env["o"], deleted=[{"kind": "task", "item_id": "o-1"}])
    push(client, env["o"], [item("o-2", updated_at="2026-11-22T11:00:00Z", title="neu")])
    body = verified(*pull(client, env["c"], after_rev=first["next_rev"]))
    assert [d["item_id"] for d in body["deleted"]] == ["o-1"]
    assert [(i["item_id"], i["title"]) for i in body["items"]] == [("o-2", "neu")]
    again = verified(*pull(client, env["c"], after_rev=body["next_rev"]))
    assert again["items"] == [] and again["deleted"] == [] and again["next_rev"] == body["next_rev"]


def test_loeschungen_ueber_c_selbst_nicht(client, env):
    push(client, env["c"], [item("c-1")])
    push(client, env["c"], deleted=[{"kind": "task", "item_id": "c-1"}])
    assert verified(*pull(client, env["c"]))["deleted"] == []


def test_eigene_eintraege_des_hubs_mit_cursor(client, env):
    src = env["src"]
    src["task"].put("h-1", "2026-11-22T09:00:00Z")
    src["idea"].put("h-2", "2026-11-22T09:00:00.123456Z")
    src["task"].put("h-3", "2026-11-22T09:00:00Z", owner="anna")  # anderer Nutzer
    body = verified(*pull(client, env["c"]))
    own_fp = ident.fingerprint(ident.public_key_b64())
    assert _ids(body) == ["h-1", "h-2"]
    assert all(i["origin_fp"] == own_fp and i["origin_name"] is None for i in body["items"])
    assert body["local_next"]["task"][0] == "2026-11-22T09:00:00Z"
    assert body["local_next"]["idea"][0] == "2026-11-22T09:00:00.123456Z"
    src["task"].put("h-4", "2026-11-22T09:30:00Z")
    nxt = verified(*pull(client, env["c"], after_rev=body["next_rev"], local_after=body["local_next"]))
    assert "h-4" in _ids(nxt)
    # Die letzte Zeitstufe geht absichtlich noch einmal mit (wie beim Push), ältere nicht mehr
    third = verified(*pull(client, env["c"], after_rev=nxt["next_rev"], local_after=nxt["local_next"]))
    assert [i["item_id"] for i in third["items"] if i["kind"] == "task"] == ["h-4"]


def test_eigene_eintraege_beachten_auswahl_und_ausschluss_des_hubs(client, admin_headers, env):
    env["src"]["task"].put("h-1", "2026-11-22T09:00:00Z", project_id="geheim")
    env["src"]["task"].put("h-2", "2026-11-22T09:00:00Z")
    settings(client, admin_headers, excluded=["geheim"])
    assert _ids(verified(*pull(client, env["c"]))) == ["h-2"]
    settings(client, admin_headers, users=())                     # Hub wählt niemanden aus
    assert verified(*pull(client, env["c"]))["items"] == []


def test_kaputte_quelle_laesst_art_aus(client, env):
    env["src"]["task"].fail = True
    env["src"]["idea"].put("h-2", "2026-11-22T09:00:00Z")
    body = verified(*pull(client, env["c"], local_after={"task": ["2026-01-01T00:00:00Z", "x"], "idea": None}))
    assert _ids(body) == ["h-2"]
    assert body["local_next"]["task"] == ["2026-01-01T00:00:00Z", "x"]   # Cursor bleibt stehen


def test_reset_local_bis_c_von_vorn_holt(client, env):
    with db() as conn:
        conn.execute("UPDATE federation_catalog_sources SET reset_local = 1 WHERE peer_id = ?", (env["c_peer"]["id"],))
    cursor = {"task": ["2026-11-22T09:00:00Z", ""], "idea": None}
    assert verified(*pull(client, env["c"], local_after=cursor))["reset_local"] is True
    assert verified(*pull(client, env["c"], local_after=cursor))["reset_local"] is True   # Antwort verloren
    assert verified(*pull(client, env["c"]))["reset_local"] is False                      # C holt von vorn
    assert verified(*pull(client, env["c"], local_after=cursor))["reset_local"] is False


def test_instances_mit_hub_und_o_ohne_c(client, env):
    push(client, env["o"], [item("o-1")])
    body = verified(*pull(client, env["c"]))
    names = [i["origin_name"] for i in body["instances"]]
    assert names == [None, "devbox"]                              # Hub selbst, dann O; C fehlt
    assert body["instances"][1]["stale"] is False and body["instances"][0]["origin_fp"]
