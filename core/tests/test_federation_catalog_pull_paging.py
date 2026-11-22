"""G2/V2 — catalog_pull: Blättern (≤ 500, more, next_rev), full_keys (≤ 5000 je
Seite, keys_next/keys_after) und voller Abgleich bei after_rev < min_partial_rev.
"""
from __future__ import annotations

import pytest

from hydrahive.db.connection import db
from hydrahive.federation import catalog_pull, peer_identity as ident
from tests._catalog_pull_env import item, pull, push, verified

pytest_plugins = ["tests._catalog_pull_env"]  # Fixture `env`


def test_echte_grenzen():
    assert catalog_pull.MAX_LIMIT == 500 and catalog_pull.MAX_KEYS == 5000


def test_hoechstens_500_je_seite_auch_wenn_mehr_verlangt(client, env):
    push(client, env["o"], [item(f"o-{n:03d}") for n in range(500)])
    push(client, env["o"], [item("o-500")])
    first = verified(*pull(client, env["c"], limit=9999))
    assert len(first["items"]) == 500 and first["more"] is True
    rest = verified(*pull(client, env["c"], after_rev=first["next_rev"]))
    assert [i["item_id"] for i in rest["items"]] == ["o-500"] and rest["more"] is False


def test_blaettern_ueber_eintraege_und_loeschungen(client, env):
    push(client, env["o"], [item("o-1"), item("o-2"), item("o-3")])
    push(client, env["o"], deleted=[{"kind": "task", "item_id": "o-1"}])
    seen, deleted, after, pages = [], [], 0, 0
    while True:
        body = verified(*pull(client, env["c"], after_rev=after, limit=1))
        assert len(body["items"]) + len(body["deleted"]) <= 1
        seen += [i["item_id"] for i in body["items"]]
        deleted += [d["item_id"] for d in body["deleted"]]
        assert body["next_rev"] >= after
        after, pages = body["next_rev"], pages + 1
        if not body["more"]:
            break
        assert pages < 10
    assert sorted(seen) == ["o-2", "o-3"] and deleted == ["o-1"]   # o-1 ist schon weg, kommt nur als Löschung


def test_eigene_eintraege_fuellen_den_rest_der_seite(client, env):
    push(client, env["o"], [item("o-1")])
    env["src"]["task"].put("h-1", "2026-11-22T09:00:00Z")
    env["src"]["task"].put("h-2", "2026-11-22T09:00:01Z")
    first = verified(*pull(client, env["c"], limit=2))
    assert [i["item_id"] for i in first["items"]] == ["o-1", "h-1"] and first["more"] is True
    assert first["local_next"]["task"] == ["2026-11-22T09:00:00Z", "h-1"]       # Keyset mitten im Blättern
    rest = verified(*pull(client, env["c"], after_rev=first["next_rev"], local_after=first["local_next"], limit=2))
    assert [i["item_id"] for i in rest["items"]] == ["h-2"] and rest["more"] is False


def _all_keys(client, env, **kw):
    keys, after, pages = [], None, 0
    while True:
        body = verified(*pull(client, env["c"], full=True, keys_after=after, **kw))
        assert body["full"] is True and body["full_keys"] is not None
        keys += body["full_keys"]
        pages += 1
        after = body["keys_next"]
        if after is None:
            return keys, pages
        assert body["more"] is True and pages < 20


def test_full_keys_vollstaendig_ohne_eigene_von_c(client, env):
    push(client, env["o"], [item("o-1"), item("o-2", owner="anna")])
    push(client, env["c"], [item("c-1")])
    env["src"]["idea"].put("h-1", "2026-11-22T09:00:00Z")
    keys, pages = _all_keys(client, env)
    own_fp = ident.fingerprint(ident.public_key_b64())
    assert pages == 1
    assert sorted(keys) == sorted([[env["o"].fp, "task", "o-1", item("o-1")["updated_at"]],
                                   [own_fp, "idea", "h-1", "2026-11-22T09:00:00Z"]])


def test_full_keys_seitenweise(client, env, monkeypatch):
    monkeypatch.setattr(catalog_pull, "MAX_KEYS", 2)
    push(client, env["o"], [item(f"o-{n}") for n in range(5)])
    keys, pages = _all_keys(client, env)
    assert pages == 3 and sorted(k[2] for k in keys) == [f"o-{n}" for n in range(5)]
    assert len({tuple(k) for k in keys}) == 5                    # nichts doppelt


def test_full_keys_mit_kaputter_quelle_abgelehnt(client, env):
    env["src"]["task"].fail = True
    r, _ = pull(client, env["c"], full=True)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "peer_local_failed"


def test_ohne_full_keine_schluessel(client, env):
    body = verified(*pull(client, env["c"]))
    assert body["full"] is False and body["full_keys"] is None and body["keys_next"] is None


@pytest.fixture
def purged():
    with db() as conn:
        old = conn.execute("SELECT purged_rev FROM federation_catalog_counter WHERE id = 1").fetchone()[0]
    yield
    with db() as conn:
        conn.execute("UPDATE federation_catalog_counter SET purged_rev = ? WHERE id = 1", (old,))


def test_zu_alter_stand_bekommt_vollen_abgleich(client, env, purged):
    push(client, env["o"], [item("o-1")])
    first = verified(*pull(client, env["c"]))
    with db() as conn:                                           # Löschprotokoll bis hier aufgeräumt
        conn.execute("UPDATE federation_catalog_counter SET purged_rev = ? WHERE id = 1", (first["next_rev"],))
    body = verified(*pull(client, env["c"], after_rev=1))
    assert body["full"] is True and body["full_keys"] is not None
    assert [i["item_id"] for i in body["items"]] == ["o-1"]      # wieder von vorn
    normal = verified(*pull(client, env["c"], after_rev=first["next_rev"]))
    assert normal["full"] is False                               # aktueller Stand: kein voller Abgleich
    fresh = verified(*pull(client, env["c"], after_rev=0))
    assert fresh["full"] is False                                # 0 heißt „von vorn“, ohne Schlüsselliste
