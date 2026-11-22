"""F2 (MEDIUM aus Security-Review #742): Eine Pull-Antwort bleibt auch bei großen Katalogen
mit langen Titeln und voller Schlüsselliste unter der Lesegrenze des Clients
(peer_outbound.MAX_REPLY_BYTES), und der volle Abgleich läuft trotzdem vollständig durch.
"""
from __future__ import annotations

import pytest

from hydrahive.federation import catalog_hub, catalog_pull, peer_outbound
from tests._catalog_pull_env import item, pull, push, verified

pytest_plugins = ["tests._catalog_pull_env"]

BIG = "😀" * 300                     # 300 Zeichen, 1200 Byte: größter erlaubter Titel/Projektname


def _big_item(n: int) -> dict:
    return item(f"{n:04d}-" + "x" * 123, title=BIG, project_name=BIG)


def _collect(client, env, *, full=True):
    """Wie der Client: blättern, solange ``more``; nach der ersten Antwort mit full weiter."""
    after, local, keys_after = env["base"], None, None
    items, keys, sizes = {}, set(), []
    for _ in range(200):
        r, p = pull(client, env["c"], after_rev=after, local_after=local, full=full, keys_after=keys_after)
        sizes.append(len(r.content))
        body = verified(r, p)
        items.update({i["item_id"]: i for i in body["items"]})
        keys.update(tuple(k[:3]) for k in body["full_keys"] or [])
        after, local, keys_after = body["next_rev"], body["local_next"], body["keys_next"]
        full = full or body["full"]
        if not body["more"]:
            return items, keys, sizes
    raise AssertionError("Abgleich endet nicht")


@pytest.fixture
def no_rate_limit(monkeypatch):
    monkeypatch.setattr(catalog_hub, "_RATE_MAX", 10_000)


def test_budget_unter_der_lesegrenze():
    assert catalog_pull.PAGE_BYTES + 32_768 < peer_outbound.MAX_REPLY_BYTES


def test_grosser_katalog_bleibt_unter_der_grenze_und_laeuft_durch(client, env, no_rate_limit):
    for start in range(0, 700, 100):                          # Push-Anfragen ≤ 1 MB (Grenze des Hubs)
        push(client, env["o"], [_big_item(n) for n in range(start, start + 100)])
    items, keys, sizes = _collect(client, env)
    assert max(sizes) <= peer_outbound.MAX_REPLY_BYTES, sizes
    assert len(sizes) > 1                                     # hätte vorher in eine Seite gemusst
    assert len(items) == 700 and all(i["title"] == BIG for i in items.values())
    assert len(keys) == 700


def test_viele_schluessel_werden_nach_bytes_geteilt(client, env, no_rate_limit, monkeypatch):
    monkeypatch.setattr(catalog_pull, "PAGE_BYTES", 20_000)  # klein, damit Seiten entstehen
    push(client, env["o"], [_big_item(n) for n in range(60)])
    items, keys, sizes = _collect(client, env)
    assert len(items) == 60 and len(keys) == 60
    assert max(sizes) <= 20_000 + 32_768                     # Budget + Umschlag
    assert len(sizes) >= 4


def test_ohne_full_auch_nach_bytes(client, env, no_rate_limit, monkeypatch):
    monkeypatch.setattr(catalog_pull, "PAGE_BYTES", 15_000)
    push(client, env["o"], [_big_item(n) for n in range(40)])
    items, keys, sizes = _collect(client, env, full=False)
    assert len(items) == 40 and keys == set()
    assert max(sizes) <= 15_000 + 32_768 and len(sizes) >= 3


def test_eigene_eintraege_des_hubs_auch_nach_bytes(client, env, no_rate_limit, monkeypatch):
    monkeypatch.setattr(catalog_pull, "PAGE_BYTES", 15_000)
    for n in range(30):
        env["src"]["task"].put(f"h-{n:03d}", f"2026-11-22T09:{n:02d}:00Z")
        env["src"]["task"].rows[("testuser", f"h-{n:03d}")]["title"] = BIG
    items, _keys, sizes = _collect(client, env, full=False)
    assert len([i for i in items if i.startswith("h-")]) == 30
    assert max(sizes) <= 15_000 + 32_768 and len(sizes) >= 3
