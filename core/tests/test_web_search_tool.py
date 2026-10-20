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


# --- Spec websuche-kostenlos §4: Kategorie, Zeitraum, Datum/Quelle, News-Wechsel ---------


class _Recorder:
    """Gefälschter SearXNG-Client: merkt sich jede Anfrage, Antworten der Reihe nach."""
    calls: list = []
    answers: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, **k):
        type(self).calls.append(dict(params or {}))
        answers = type(self).answers
        return _Resp(answers.pop(0) if len(answers) > 1 else answers[0])


@pytest.fixture
def searx(monkeypatch):
    _Recorder.calls = []
    _Recorder.answers = [{"results": [HIT]}]
    monkeypatch.setattr(ws.httpx, "AsyncClient", _Recorder)
    monkeypatch.setattr(ws, "resolve_setting", lambda key: "http://searx.test:8888" if key == "searxng_url" else "")
    return _Recorder


def _search(**args):
    return asyncio.run(ws._execute({"query": "afd leak", **args}, _ctx()))


def test_without_new_params_request_is_unchanged(searx):
    _search()
    assert searx.calls == [{"q": "afd leak", "format": "json", "language": "de"}]


def test_category_and_time_range_are_passed_to_searxng(searx):
    _search(category="news", time_range="week")
    assert searx.calls[0]["categories"] == "news"
    assert searx.calls[0]["time_range"] == "week"


@pytest.mark.parametrize("bad", [{"category": "images"}, {"category": "NEWS; drop"},
                                 {"time_range": "hour"}, {"time_range": ""}, {"category": 3}])
def test_invalid_category_or_time_range_fails_without_request(searx, bad):
    res = _search(**bad)
    assert res.success is False
    assert searx.calls == []


def test_hits_carry_source_and_date_only_when_known(searx):
    searx.answers = [{"results": [
        {**HIT, "engine": "bing news", "publishedDate": "2026-10-20T08:41:00"},
        {**HIT, "url": "https://b.example", "engine": "bing"},
    ]}]
    res = _search()
    first, second = res.output["results"]
    assert first["source"] == "bing news"
    assert first["published"] == "2026-10-20"
    assert second["source"] == "bing"
    assert "published" not in second


def test_general_with_time_range_and_no_hits_retries_once_as_news(searx):
    searx.answers = [{"results": []}, {"results": [HIT]}]
    res = _search(time_range="week")
    assert [c.get("categories") for c in searx.calls] == [None, "news"]
    assert searx.calls[1]["time_range"] == "week"
    assert res.output["fallback"] == "news"
    assert res.output["count"] == 1


def test_no_news_retry_without_time_range(searx):
    searx.answers = [{"results": []}]
    res = _search()
    assert len(searx.calls) == 1
    assert "fallback" not in res.output


def test_no_news_retry_when_already_news(searx):
    searx.answers = [{"results": []}]
    _search(category="news", time_range="day")
    assert len(searx.calls) == 1


# --- Spec websuche-kostenlos §5: Tavily als Ersatz ---------------------------------------


@pytest.fixture
def tavily(monkeypatch, searx):
    """Tavily-Aufruf + Zähler gefälscht; Schlüssel per Setting."""
    state = {"calls": [], "key": "tvly-GEHEIM123", "allow": True, "raise": None,
             "answer": {"results": [{"title": "T", "url": "https://t.example", "snippet": "s",
                                     "published": "2026-10-20", "source": "tavily"}]}}

    async def fake_search(query, *, topic, time_range, count, api_key):
        state["calls"].append({"query": query, "topic": topic, "time_range": time_range,
                               "count": count, "api_key": api_key})
        if state["raise"]:
            raise state["raise"]
        return state["answer"]

    monkeypatch.setattr(ws._tavily, "search", fake_search)
    monkeypatch.setattr(ws._tavily, "reserve", lambda: state["allow"])
    monkeypatch.setattr(ws, "resolve_setting",
                        lambda key: {"searxng_url": "http://searx.test:8888",
                                     "tavily_api_key": state["key"]}.get(key, ""))
    return state


def test_without_key_tavily_is_never_called(searx, tavily):
    tavily["key"] = ""
    searx.answers = [{"results": [], "unresponsive_engines": BLOCKED}]
    res = _search()
    assert tavily["calls"] == []
    assert res.success is False


def test_searx_hits_do_not_touch_tavily(searx, tavily):
    res = _search()
    assert tavily["calls"] == []
    assert res.output.get("provider", "searxng") == "searxng"


def test_blocked_and_empty_falls_back_to_tavily(searx, tavily):
    searx.answers = [{"results": [], "unresponsive_engines": BLOCKED}]
    res = _search(category="news", time_range="week", count=5)
    assert res.success is True
    assert res.output["provider"] == "tavily"
    assert res.output["results"][0]["source"] == "tavily"
    assert res.output["unavailable"][0]["engine"] == "duckduckgo"
    assert tavily["calls"] == [{"query": "afd leak", "topic": "news", "time_range": "week",
                                "count": 5, "api_key": "tvly-GEHEIM123"}]


def test_searx_http_error_falls_back_to_tavily(monkeypatch, searx, tavily):
    class Boom(_Recorder):
        async def get(self, *a, **k):
            raise httpx.ConnectError("All connection attempts failed")

    monkeypatch.setattr(ws.httpx, "AsyncClient", Boom)
    res = _search()
    assert res.success is True
    assert res.output["provider"] == "tavily"


def test_empty_without_outage_does_not_use_tavily(searx, tavily):
    searx.answers = [{"results": [], "unresponsive_engines": []}]
    res = _search()
    assert tavily["calls"] == []
    assert res.output["count"] == 0


def test_exhausted_quota_reports_both_findings(searx, tavily):
    tavily["allow"] = False
    searx.answers = [{"results": [], "unresponsive_engines": BLOCKED}]
    res = _search()
    assert res.success is False
    assert tavily["calls"] == []
    assert "Tavily-Monatskontingent" in res.error
    assert "duckduckgo (CAPTCHA)" in res.error


def test_tavily_error_never_leaks_key(searx, tavily):
    tavily["raise"] = ws._tavily.TavilyError("Tavily: HTTP 401")
    searx.answers = [{"results": [], "unresponsive_engines": BLOCKED}]
    res = _search()
    assert res.success is False
    assert "HTTP 401" in res.error
    assert "duckduckgo (CAPTCHA)" in res.error
    assert "GEHEIM" not in res.error
