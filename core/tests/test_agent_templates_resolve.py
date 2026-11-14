"""Template-Auflösung zur Laufzeit (Plan E2 T3)."""
from __future__ import annotations

import logging

import pytest

from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: {
        "claude-opus-5-5", "claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"})
    _store.reset_cache()
    yield
    _store.reset_cache()


def test_agent_mit_template():
    r = tpl.resolve({"template": "projekt-master"})
    assert r is not None and r.id == "projekt-master"
    assert r.chain == ["claude-opus-5-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"]
    assert r.max_iterations == 60 and r.reasoning_effort == "high" and r.overrun_pct == 20


def test_agent_ohne_template_ist_none():
    assert tpl.resolve({"llm_model": "x"}) is None
    assert tpl.resolve({}) is None


def test_unbekanntes_template_faellt_zurueck_mit_warnung(caplog):
    with caplog.at_level(logging.WARNING):
        r = tpl.resolve({"template": "gibts-nicht"})
    assert r is not None and r.id == "assistant"
    assert any("gibts-nicht" in rec.getMessage() for rec in caplog.records)


def test_systemrolle_per_name():
    r = tpl.resolve_role("kompaktierung")
    assert r is not None and r.chain[0] == "claude-sonnet-5"


def test_aenderung_wirkt_beim_naechsten_aufloesen():
    t = tpl.get("reviewer")
    t["budget"]["max_iterations"] = 120
    tpl.save("reviewer", t, by="admin")
    assert tpl.resolve({"template": "reviewer"}).max_iterations == 120


def test_ohne_bekannte_modelle_kein_absturz(monkeypatch):
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: set())
    _store.reset_cache()
    assert tpl.resolve({"template": "buddy"}) is None
