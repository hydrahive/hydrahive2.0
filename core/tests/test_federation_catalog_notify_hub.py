"""G2/V7 — Hub stupst an (docs/specs/federation-shared-tasks.md §Anstupsen catalog_notify):
Bündelung (≤ 1 je Client und 10 s, keine Wiederholung), nur berechtigte Empfänger,
Auslöser (Push, eigene Verteilung, Sichtbarkeit), Fehler beim Senden blockiert nichts.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.federation import catalog_notify, catalog_runner, peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from tests._catalog_pull_env import _pair, item, push, settings

pytest_plugins = ["tests._catalog_pull_env"]


@pytest.fixture
def sent(monkeypatch):
    catalog_notify._reset_for_tests()
    log: list[tuple[str, dict]] = []
    state = {"fail": set(), "slow": set()}

    async def fake_send(peer, payload):
        if peer["name"] in state["slow"]:
            await asyncio.sleep(30)
        log.append((peer["name"], payload))
        if peer["name"] in state["fail"]:
            raise RuntimeError("Client weg")
        return True
    monkeypatch.setattr(catalog_notify, "_send", fake_send)
    yield log, state
    catalog_notify._reset_for_tests()


def _names(log):
    return sorted(n for n, _ in log)


def test_new_catalog_notify_form():
    p = proto.new_catalog_notify(42)
    assert set(p) == {"kind", "msg_id", "from", "issued_at", "rev"}
    assert p["kind"] == "catalog_notify" and p["rev"] == 42
    assert p["from"] == ident.fingerprint(ident.public_key_b64())


async def test_push_stupst_die_anderen_an_nicht_den_absender(client, env, sent):
    log, _ = sent
    catalog_notify._reset_for_tests()
    push(client, env["o"], [item("o-1")])
    assert await catalog_notify.flush() == 1
    assert _names(log) == ["hydrahome"]                       # C ja, O (Absender) nein
    assert log[0][1]["kind"] == "catalog_notify" and "items" not in log[0][1]


async def test_leerer_push_stupst_nicht_an(client, env, sent):
    log, _ = sent
    push(client, env["o"], [])                                # O wird sichtbar (darf anstupsen)
    catalog_notify._reset_for_tests()
    push(client, env["o"], [])                                # nur Lebenszeichen
    assert await catalog_notify.flush() == 0 and log == []


async def test_buendelung_hoechstens_einer_je_client_und_10_s(client, env, sent):
    log, _ = sent
    catalog_notify._reset_for_tests()
    for n in range(5):
        push(client, env["o"], [item(f"o-{n}")])
    assert await catalog_notify.flush(now=100.0) == 1         # fünf Änderungen, ein Anstupser
    push(client, env["o"], [item("o-9")])
    assert await catalog_notify.flush(now=105.0) == 0         # im Fenster: wartet
    assert catalog_notify.pending()
    assert await catalog_notify.flush(now=110.0) == 1         # nach 10 s genau einer
    assert await catalog_notify.flush(now=200.0) == 0         # keine Wiederholung ohne Änderung
    assert len(log) == 2


async def test_nur_berechtigte_empfaenger(client, admin_headers, env, sent):
    log, _ = sent
    third_fp, third = _pair(client, admin_headers, "dritte")  # meldet shared nie
    push(client, env["o"], [], shared=True)
    catalog_notify._reset_for_tests()
    catalog_notify.mark()                                     # eigene Änderung des Hubs
    await catalog_notify.flush()
    assert _names(log) == ["devbox", "hydrahome"]             # „dritte“ ohne shared nicht
    log.clear()
    client.post(f"/api/federation/peers/{env['c_peer']['id']}/block", headers=admin_headers)
    catalog_notify._reset_for_tests()
    catalog_notify.mark()
    await catalog_notify.flush()
    assert _names(log) == ["devbox"]                          # gesperrt: nein
    client.delete(f"/api/federation/peers/{third['id']}", headers=admin_headers)
    _ = third_fp


async def test_hub_ohne_shared_stupst_nicht_an(client, admin_headers, env, sent):
    log, _ = sent
    settings(client, admin_headers, shared=False)
    catalog_notify._reset_for_tests()
    catalog_notify.mark()
    assert await catalog_notify.flush() == 0 and log == []


async def test_eigene_verteilung_stupst_an(client, env, sent, monkeypatch):
    log, _ = sent
    catalog_notify._reset_for_tests()
    monkeypatch.setattr(catalog_runner.catalog_hub_own, "hub_distribute_step", lambda: True)
    assert await catalog_runner.hub_tick() is True
    await catalog_notify.flush()
    assert _names(log) == ["hydrahome"]                       # O meldet (noch) kein shared
    monkeypatch.setattr(catalog_runner.catalog_hub_own, "hub_distribute_step", lambda: False)
    catalog_notify._reset_for_tests()
    assert await catalog_runner.hub_tick() is False
    assert not catalog_notify.pending()


async def test_wegfall_der_sichtbarkeit_stupst_an(client, env, sent):
    log, _ = sent
    push(client, env["o"], [item("o-1")])
    catalog_notify._reset_for_tests()
    push(client, env["o"], [], shared=False)                  # O teilt nicht mehr → Löschzeilen
    await catalog_notify.flush()
    assert _names(log) == ["hydrahome"]


async def test_fehler_beim_senden_blockiert_nichts(client, admin_headers, env, sent):
    log, state = sent
    push(client, env["o"], [], shared=True)
    state["fail"] = {"hydrahome"}
    catalog_notify._reset_for_tests()
    catalog_notify.mark()
    assert await catalog_notify.flush() == 1                  # devbox trotzdem
    assert _names(log) == ["devbox", "hydrahome"]
    assert not catalog_notify.pending()                       # keine Wiederholung


async def test_langsamer_client_haelt_andere_nicht_auf(client, env, sent, monkeypatch):
    log, state = sent
    push(client, env["o"], [], shared=True)
    state["slow"] = {"hydrahome"}
    real = catalog_notify._send

    async def bounded(peer, payload):
        try:
            return await asyncio.wait_for(real(peer, payload), timeout=0.2)
        except asyncio.TimeoutError:
            return False
    monkeypatch.setattr(catalog_notify, "_send", bounded)
    catalog_notify._reset_for_tests()
    catalog_notify.mark()
    assert await asyncio.wait_for(catalog_notify.flush(), timeout=2) == 1
    assert _names(log) == ["devbox"]


async def test_echtes_senden_faengt_netzfehler(env):
    peer = {"name": "weg", "url": "https://127.0.0.1:9"}
    assert await catalog_notify._send(peer, proto.new_catalog_notify(1)) is False


async def test_partner_entfernen_und_ausschluss_beim_hub_stupsen_an(client, admin_headers, env, sent):
    """Review #742: Löschungen durch Entfernen eines Ursprungs bzw. Ausschluss beim Hub
    erreichen die Clients sofort (Anstupsen), nicht erst beim Timer."""
    log, _ = sent
    push(client, env["o"], [item("o-1")])
    catalog_notify._reset_for_tests()
    client.delete(f"/api/federation/peers/{env['o_peer']['id']}", headers=admin_headers)
    await catalog_notify.flush(now=1000.0)
    assert _names(log) == ["hydrahome"]
    log.clear()
    settings(client, admin_headers, users=())                 # Hub wählt den Nutzer ab
    await catalog_notify.flush(now=2000.0)
    assert _names(log) == ["hydrahome"]
