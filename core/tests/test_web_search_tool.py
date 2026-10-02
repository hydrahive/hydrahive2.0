"""web_search: gesperrte Suchanbieter sichtbar machen (Spec websearch-blocked-engines §4).

Am 02.10.2026 lieferte jede Suche 0 Treffer: DuckDuckGo/Startpage zeigten
CAPTCHAs, Brave meldete „zu viele Anfragen“, Google blieb leer. Das Werkzeug
gab „ok, count 0“ zurück und verwarf SearXNGs unresponsive_engines, deshalb
arbeiteten Agenten unbemerkt ohne Websuche weiter.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from hydrahive.tools import web_search as ws
from hydrahive.tools.base import ToolContext


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    payload: dict = {}

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, *a, **k):
        return _Resp(type(self).payload)


def _ctx() -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("/tmp"))


def _run(monkeypatch, payload, query="wetter berlin"):
    _Client.payload = payload
    monkeypatch.setattr(ws.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(ws, "resolve_setting", lambda key: "http://searx.test:8888")
    return asyncio.run(ws._execute({"query": query}, _ctx()))


HIT = {"title": "Wetter Berlin", "url": "https://wetter.example", "content": "21 Grad"}
BLOCKED = [["duckduckgo", "CAPTCHA"], ["brave", "Ausgesetzt: zu viele Anfragen"]]


def test_all_blocked_and_no_results_is_an_error(monkeypatch):
    res = _run(monkeypatch, {"results": [], "unresponsive_engines": BLOCKED})

    assert res.success is False
    assert "duckduckgo (CAPTCHA)" in res.error
    assert "brave (Ausgesetzt: zu viele Anfragen)" in res.error
    assert "SearXNG" in res.error


def test_results_with_partial_outage_stay_ok_and_list_unavailable(monkeypatch):
    res = _run(monkeypatch, {"results": [HIT], "unresponsive_engines": BLOCKED})

    assert res.success is True
    assert res.output["count"] == 1
    assert res.output["unavailable"] == [
        {"engine": "duckduckgo", "reason": "CAPTCHA"},
        {"engine": "brave", "reason": "Ausgesetzt: zu viele Anfragen"},
    ]


def test_no_results_without_outage_is_a_normal_empty_result(monkeypatch):
    res = _run(monkeypatch, {"results": [], "unresponsive_engines": []})

    assert res.success is True
    assert res.output["count"] == 0
    assert "unavailable" not in res.output


@pytest.mark.parametrize("broken", [None, "CAPTCHA", [["nur-name"]], [[1, 2, 3]], [None], [["", "x"]]])
def test_broken_unresponsive_field_never_crashes(monkeypatch, broken):
    res = _run(monkeypatch, {"results": [HIT], "unresponsive_engines": broken})

    assert res.success is True
    assert res.output.get("unavailable", []) == []


def test_long_reason_is_shortened(monkeypatch):
    res = _run(monkeypatch, {"results": [], "unresponsive_engines": [["google", "x" * 500]]})

    assert res.success is False
    assert "x" * 81 not in res.error
    assert "google (" in res.error


def test_http_error_still_reported(monkeypatch):
    class Boom(_Client):
        async def get(self, *a, **k):
            raise httpx.ConnectError("All connection attempts failed")

    monkeypatch.setattr(ws.httpx, "AsyncClient", Boom)
    monkeypatch.setattr(ws, "resolve_setting", lambda key: "http://searx.test:8888")
    res = asyncio.run(ws._execute({"query": "x"}, _ctx()))

    assert res.success is False
    assert "fehlgeschlagen" in res.error
