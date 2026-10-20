"""fetch_url: Browser-Kennung + format="text" (Spec websuche-kostenlos §6)."""
from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

import pytest

from hydrahive.tools import fetch_url as fu
from hydrahive.tools.base import ToolContext

PAGE = ("<html><head><title>T</title><meta property='og:title' content='Artikel'>"
        "<meta property='article:published_time' content='2026-10-20T00:22:01+00:00'>"
        "<script>var x = 1;</script></head><body><nav>Menü</nav><article><h1>Überschrift</h1><p>"
        + "Satz mit Inhalt. " * 30 + "</p></article></body></html>")


class _Resp:
    def __init__(self, content: bytes, ctype: str, status: int = 200):
        self.content = content
        self.status_code = status
        self.headers = {"content-type": ctype}


class _Client:
    sent: list = []
    resp: _Resp = _Resp(PAGE.encode(), "text/html; charset=utf-8")

    async def request(self, method, url, headers=None, params=None, content=None):
        type(self).sent.append({"method": method, "url": url, "headers": dict(headers or {})})
        return type(self).resp


@pytest.fixture
def client(monkeypatch):
    _Client.sent = []
    _Client.resp = _Resp(PAGE.encode(), "text/html; charset=utf-8")

    @contextlib.asynccontextmanager
    async def fake_safe_client(url, *, timeout):
        yield _Client()

    monkeypatch.setattr(fu, "safe_async_client", fake_safe_client)
    monkeypatch.setattr(fu, "_select_cred", lambda *a, **k: None)
    monkeypatch.setattr(fu, "_is_blocked", lambda host: False)
    return _Client


def _ctx() -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("/tmp"))


def _fetch(**args):
    return asyncio.run(fu._execute({"url": "https://borncity.example/artikel", **args}, _ctx()))


def test_browser_headers_are_sent_by_default(client):
    _fetch()
    h = client.sent[0]["headers"]
    assert h["User-Agent"].startswith("Mozilla/5.0")
    assert h["Accept-Language"].startswith("de-DE")
    assert "text/html" in h["Accept"]


def test_caller_headers_win(client):
    _fetch(headers={"User-Agent": "MeinBot/1.0"})
    assert client.sent[0]["headers"]["User-Agent"] == "MeinBot/1.0"


def test_default_format_is_raw_as_before(client):
    res = _fetch()
    assert res.success is True
    assert res.output["body"] == PAGE
    assert "format_applied" not in res.output


def test_raw_still_capped_at_200kb(client):
    client.resp = _Resp(b"a" * 300_000, "text/html")
    res = _fetch()
    assert len(res.output["body"]) == 200_000
    assert res.output["truncated"] is True


def test_text_format_returns_readable_text(client):
    res = _fetch(format="text")
    out = res.output
    assert out["format_applied"] == "text"
    assert out["body"].startswith("# Überschrift")
    assert "var x" not in out["body"]
    assert "Menü" not in out["body"]
    assert out["title"] == "Artikel"
    assert out["published"] == "2026-10-20T00:22:01+00:00"
    assert out["truncated"] is False
    assert "hint" not in out


def test_text_format_on_json_stays_raw(client):
    payload = json.dumps({"a": 1})
    client.resp = _Resp(payload.encode(), "application/json")
    res = _fetch(format="text")
    assert res.output["body"] == payload
    assert res.output["format_applied"] == "raw"


def test_almost_empty_text_hints_at_web_browser(client):
    client.resp = _Resp(b"<html><body><div id='app'></div><script>render()</script></body></html>", "text/html")
    res = _fetch(format="text")
    assert "web_browser" in res.output["hint"]


def test_long_text_is_cut_at_50000(client):
    big = "<html><body><article><p>" + "Wort " * 30_000 + "</p></article></body></html>"
    client.resp = _Resp(big.encode(), "text/html")
    res = _fetch(format="text")
    assert len(res.output["body"]) == 50_000
    assert res.output["truncated"] is True


def test_text_format_reads_beyond_raw_cap(client):
    filler = "<script>" + "z" * 300_000 + "</script>"
    page = f"<html><head>{filler}</head><body><article><p>{'Spät im Dokument. ' * 20}</p></article></body></html>"
    client.resp = _Resp(page.encode(), "text/html")
    res = _fetch(format="text")
    assert "Spät im Dokument." in res.output["body"]


def test_invalid_format_fails_without_request(client):
    res = _fetch(format="markdown")
    assert res.success is False
    assert client.sent == []
