"""Zahnfee pro Nutzer (MED-4).

Vorher: eine globale Briefing-Datei aus den Aktivitäten ALLER Nutzer, und
jeder eingeloggte Nutzer konnte sie lesen. Die Soul nannte fest "Till".
"""
from __future__ import annotations

import asyncio

import pytest


def _briefing(tag: str):
    from hydrahive.zahnfee import storage
    return storage.Briefing(generated_at="2026-09-28T03:00:00+00:00", date="2026-09-28",
                            open_items=tag, went_well="", went_badly="", today="")


def test_briefing_je_nutzer_getrennt(setup_test_env):
    from hydrahive.zahnfee import storage
    storage.save(_briefing("von alice"), "alice")
    assert storage.load("alice").open_items == "von alice"
    assert storage.load("bob") is None


def test_api_liefert_nur_eigenes_briefing(client, auth_headers, admin_headers):
    from hydrahive.zahnfee import storage
    storage.save(_briefing("geheim vom admin"), "admin")
    storage.save(_briefing("eigenes"), "testuser")
    r = client.get("/api/zahnfee/briefing", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["briefing"]["open_items"] == "eigenes"
    r = client.get("/api/zahnfee/briefing", headers=admin_headers)
    assert r.json()["briefing"]["open_items"] == "geheim vom admin"


@pytest.fixture
def fake_llm(monkeypatch):
    calls: dict = {"search": [], "llm": []}

    async def search_events(q, **kw):
        calls["search"].append(kw)
        return [{"created_at": "2026-09-27T10:00", "agent_name": "Buddy", "event_type": "user_input",
                 "snippet": "Hallo"}] if kw.get("username") == "alice" else []

    async def complete(messages, **kw):
        calls["llm"].append(messages)
        return '{"open": "o", "went_well": "w", "went_badly": "", "today": "t"}'

    monkeypatch.setattr("hydrahive.db.mirror._pool", object(), raising=False)
    monkeypatch.setattr("hydrahive.db.mirror_query.search_events", search_events)
    monkeypatch.setattr("hydrahive.llm.client.complete", complete)
    return calls


def test_run_filtert_events_nach_nutzer_und_speichert_pro_nutzer(setup_test_env, fake_llm):
    from hydrahive.zahnfee import runner, storage
    b = asyncio.run(runner.run("alice"))
    assert fake_llm["search"][0]["username"] == "alice"
    assert b.open_items == "o"
    assert storage.load("alice").open_items == "o"
    user_msg = fake_llm["llm"][0][1]["content"]
    assert "alice" in user_msg


def test_run_all_ueberspringt_nutzer_ohne_aktivitaet(setup_test_env, fake_llm, monkeypatch):
    from hydrahive.zahnfee import runner, storage
    monkeypatch.setattr("hydrahive.zahnfee.runner._usernames", lambda: ["alice", "bob"])
    asyncio.run(runner.run_all())
    assert len(fake_llm["llm"]) == 1           # kein LLM-Aufruf für bob
    assert storage.load("bob") is None


def test_default_soul_ist_neutral():
    from hydrahive.zahnfee import config
    assert "Till" not in config.DEFAULT_SOUL


def test_gespeicherte_alte_standard_soul_wird_ersetzt(setup_test_env):
    import json
    from hydrahive.zahnfee import config
    config._config_path().parent.mkdir(parents=True, exist_ok=True)
    config._config_path().write_text(json.dumps({"soul": config.LEGACY_DEFAULT_SOUL, "run_hour": 4}))
    cfg = config.load()
    assert cfg.soul == config.DEFAULT_SOUL
    assert cfg.run_hour == 4


def test_eigene_soul_bleibt_erhalten(setup_test_env):
    import json
    from hydrahive.zahnfee import config
    config._config_path().write_text(json.dumps({"soul": "Meine eigene Zahnfee"}))
    assert config.load().soul == "Meine eigene Zahnfee"
