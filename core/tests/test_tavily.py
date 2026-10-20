"""Tavily als Ersatz-Suche (Spec websuche-kostenlos §5).

Kostenlos sind 1.000 Credits pro Monat, eine Basic-Suche kostet 1 Credit (docs.tavily.com, 20.10.2026).
Der eigene Zähler hört bei 950 auf, damit das Gratis-Kontingent nie überschritten wird.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from hydrahive.tools import _tavily


class _Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


class _Client:
    sent: list = []
    resp: _Resp = _Resp()
    boom: Exception | None = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None, **k):
        type(self).sent.append({"url": url, "json": json, "headers": headers or {}})
        if type(self).boom:
            raise type(self).boom
        return type(self).resp


@pytest.fixture
def client(monkeypatch):
    _Client.sent = []
    _Client.resp = _Resp(payload={"results": [
        {"title": "AfD-Leak", "url": "https://www.spiegel.de/x", "content": "421.179 Mails",
         "published_date": "Mon, 20 Oct 2026 08:00:00 GMT", "score": 0.9},
        {"title": "Ohne Datum", "url": "https://b.example", "content": "b"},
    ]})
    _Client.boom = None
    monkeypatch.setattr(_tavily.httpx, "AsyncClient", _Client)
    return _Client


def _search(**kw):
    args = {"topic": "general", "time_range": None, "count": 10, "api_key": "tvly-GEHEIM123", **kw}
    return asyncio.run(_tavily.search("afd leak", **args))


def test_request_is_cheap_basic_search_with_key_in_header(client):
    _search(topic="news", time_range="week", count=5)
    sent = client.sent[0]
    assert sent["url"] == "https://api.tavily.com/search"
    body = sent["json"]
    assert body["query"] == "afd leak"
    assert body["search_depth"] == "basic"
    assert body["topic"] == "news"
    assert body["time_range"] == "week"
    assert body["max_results"] == 5
    for costly in ("include_answer", "include_raw_content", "include_images"):
        assert body.get(costly) in (None, False)
    assert "api_key" not in body
    assert sent["headers"]["Authorization"] == "Bearer tvly-GEHEIM123"


def test_no_time_range_field_when_not_set(client):
    _search()
    assert "time_range" not in client.sent[0]["json"]


def test_count_is_capped_at_20(client):
    _search(count=50)
    assert client.sent[0]["json"]["max_results"] == 20


def test_results_are_mapped_to_web_search_format(client):
    out = _search()
    first, second = out["results"]
    assert first == {"title": "AfD-Leak", "url": "https://www.spiegel.de/x", "snippet": "421.179 Mails",
                     "source": "tavily", "published": "Mon, 20 Oct 2026 08:00:00 GMT"}
    assert "published" not in second


@pytest.mark.parametrize("status", [401, 429, 432, 500])
def test_http_errors_never_leak_key_or_body(client, status):
    client.resp = _Resp(status=status, text='{"detail": "invalid key tvly-GEHEIM123"}')
    with pytest.raises(_tavily.TavilyError) as e:
        _search()
    msg = str(e.value)
    assert f"HTTP {status}" in msg
    assert "GEHEIM" not in msg
    assert "invalid key" not in msg


def test_timeout_is_a_tavily_error(client):
    client.boom = httpx.ReadTimeout("timed out")
    with pytest.raises(_tavily.TavilyError) as e:
        _search()
    assert "Tavily" in str(e.value)


def test_non_json_answer_is_a_tavily_error(client, monkeypatch):
    class Bad(_Resp):
        def json(self):
            raise ValueError("kein json")

    client.resp = Bad()
    with pytest.raises(_tavily.TavilyError):
        _search()


# --- Monatszähler -------------------------------------------------------------------


@pytest.fixture
def usage(tmp_path, monkeypatch):
    monkeypatch.setattr(_tavily, "_usage_path", lambda: tmp_path / "websearch" / "tavily_usage.json")
    monkeypatch.setattr(_tavily, "_month", lambda: "2026-10")
    return tmp_path / "websearch" / "tavily_usage.json"


def test_reserve_counts_each_call(usage):
    assert _tavily.reserve() is True
    assert _tavily.reserve() is True
    assert json.loads(usage.read_text()) == {"month": "2026-10", "count": 2}


def test_reserve_stops_at_950(usage):
    usage.parent.mkdir(parents=True)
    usage.write_text(json.dumps({"month": "2026-10", "count": 949}))
    assert _tavily.reserve() is True
    assert _tavily.reserve() is False
    assert json.loads(usage.read_text())["count"] == 950


def test_new_month_starts_at_zero(usage, monkeypatch):
    usage.parent.mkdir(parents=True)
    usage.write_text(json.dumps({"month": "2026-09", "count": 950}))
    assert _tavily.reserve() is True
    assert json.loads(usage.read_text()) == {"month": "2026-10", "count": 1}


@pytest.mark.parametrize("broken", ["", "{kaputt", "[]", '{"month": "2026-10", "count": "x"}'])
def test_broken_usage_file_counts_as_empty(usage, broken):
    usage.parent.mkdir(parents=True)
    usage.write_text(broken)
    assert _tavily.reserve() is True
    assert json.loads(usage.read_text()) == {"month": "2026-10", "count": 1}


def test_no_tmp_file_left_behind(usage):
    _tavily.reserve()
    assert sorted(p.name for p in usage.parent.iterdir()) == ["tavily_usage.json"]
