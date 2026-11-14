"""Module fragen eine Rolle an statt eines festen Modells (Plan E5, Kern-Teil)."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store
from hydrahive.llm import client
from hydrahive.runner import _model_cooldown as cooldown

KNOWN = {"claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    cooldown.reset()
    yield
    _store.reset_cache()
    cooldown.reset()


def _chain(tid):
    return tpl.get(tid)["chain"]


def test_complete_mit_template_nutzt_kette(monkeypatch):
    seen = []

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.append(model)
        if len(seen) == 1:
            raise TimeoutError("hängt")
        return "ok"
    monkeypatch.setattr(client, "_complete_one", fake)
    out = asyncio.run(client.complete([{"role": "user", "content": "x"}], template="modul-schnell"))
    assert out == "ok"
    assert seen == _chain("modul-schnell")[:2]


def test_unbekanntes_template_faellt_auf_standard(monkeypatch):
    seen = []

    async def fake(messages, model=None, **kw):
        seen.append(model)
        return "ok"
    monkeypatch.setattr(client, "_complete_one", fake)
    asyncio.run(client.complete([{"role": "user", "content": "x"}], template="gibt-es-nicht"))
    assert seen == [_chain("assistant")[0]]


def test_ohne_template_wie_bisher(monkeypatch):
    seen = []

    async def fake(messages, model=None, **kw):
        seen.append(model)
        return "ok"
    monkeypatch.setattr(client, "_complete_one", fake)
    asyncio.run(client.complete([{"role": "user", "content": "x"}], model="claude-sonnet-5"))
    assert seen == ["claude-sonnet-5"]


def _collect(agen):
    async def run():
        return [c async for c in agen]
    return asyncio.run(run())


def test_stream_wechselt_vor_dem_ersten_text(monkeypatch):
    seen = []

    async def fake(messages, model=None, **kw):
        seen.append(model)
        if len(seen) == 1:
            raise httpx.ConnectError("weg")
        yield "a"
        yield "b"
    monkeypatch.setattr(client, "_stream_one", fake)
    assert _collect(client.stream([{"role": "user", "content": "x"}], template="modul-schnell")) == ["a", "b"]
    assert seen == _chain("modul-schnell")[:2]


def test_stream_wechselt_nicht_nach_gesendetem_text(monkeypatch):
    seen = []

    async def fake(messages, model=None, **kw):
        seen.append(model)
        yield "a"
        raise httpx.ReadError("mittendrin")
    monkeypatch.setattr(client, "_stream_one", fake)
    with pytest.raises(httpx.ReadError):
        _collect(client.stream([{"role": "user", "content": "x"}], template="modul-schnell"))
    assert len(seen) == 1


def test_supports_template_flag():
    assert client.SUPPORTS_TEMPLATE is True
