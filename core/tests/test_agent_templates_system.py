"""Systemrollen an Templates (Plan E2 T6): Zahnfee und Lehren laufen über die Kette ihres Templates.

Ohne Template-Datei bzw. ohne nutzbares Template gilt die bisherige Einstellung als Einzelkette.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store
from hydrahive.agents.templates._system import complete_with_chain, system_chain
from hydrahive.runner import _model_cooldown as cooldown

KNOWN = {"claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    cooldown.reset()
    yield
    _store.reset_cache()
    cooldown.reset()


def test_kette_aus_template():
    assert system_chain("zahnfee", "alt") == ["claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"]


def test_ohne_template_bisherige_einstellung(monkeypatch):
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: set())
    _store.reset_cache()
    assert system_chain("zahnfee", "claude-sonnet-4-6") == ["claude-sonnet-4-6"]
    assert system_chain("zahnfee", None) == []


def test_unbekannte_rolle_nicht_auf_fremdes_template():
    assert system_chain("gibts-nicht", "x") == ["x"]


def test_heutige_einstellung_wird_primaer(monkeypatch):
    monkeypatch.setattr(tpl._defaults, "_current_system_models",
                        lambda: {"zahnfee": "openai-codex/gpt-5.6-terra"})
    _store.reset_cache()
    chain = system_chain("zahnfee")
    assert chain[0] == "openai-codex/gpt-5.6-terra" and chain[1] == "claude-sonnet-5"


def _run(chain, script):
    calls: list[str] = []

    async def fake(messages, model=None, **kw):
        calls.append(model)
        item = script[model].pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    from hydrahive.llm import client
    orig = client.complete
    client.complete = fake
    try:
        return asyncio.run(complete_with_chain(chain, [{"role": "user", "content": "x"}])), calls
    finally:
        client.complete = orig


def test_wechsel_bei_429():
    out, calls = _run(["a", "b"], {"a": [RuntimeError("Error 429")], "b": ["B"]})
    assert out == "B" and calls == ["a", "b"] and cooldown.is_down("a")


def test_wechsel_bei_leerer_antwort():
    out, calls = _run(["a", "b"], {"a": [""], "b": ["B"]})
    assert out == "B" and calls == ["a", "b"]


def test_programmfehler_kein_wechsel():
    with pytest.raises(ValueError):
        _run(["a", "b"], {"a": [ValueError("kaputt")], "b": ["B"]})


def test_letztes_modell_fehler_kommt_an():
    with pytest.raises(RuntimeError):
        _run(["a"], {"a": [RuntimeError("Error 429")]})
