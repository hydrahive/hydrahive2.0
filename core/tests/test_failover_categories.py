"""Fehlerkategorien für den Modellwechsel (Spec agent-templates.md Kap. 8, Plan E1 T1).

`classify(exc)` ordnet einen Fehler einer Kategorie zu. Daraus entscheidet die Modellkette:
- auth/quota/rate_limit/overload: Anbieter- oder Kontoproblem → nächstes Modell, Modell kurz sperren.
- timeout/stream_abort: Verbindung → nach den Wiederholversuchen nächstes Modell.
- None: kein Grund zum Wechseln (Konfig-/Programmfehler), Fehler läuft durch.

`should_failover` bleibt für die Kompaktierung unverändert (nur Anbieter-/Kontoprobleme).
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from hydrahive.runner._codex_http import CodexStreamStall
from hydrahive.runner._failover import (
    PROVIDER_CATEGORIES,
    SWITCH_CATEGORIES,
    classify,
    should_failover,
)


@pytest.mark.parametrize(("msg", "cat"), [
    ("Error 429: Too Many Requests", "rate_limit"),
    ("rate_limit_exceeded", "rate_limit"),
    ("The model is overloaded, please retry", "overload"),
    ("HTTP 529 overloaded", "overload"),
    ("authentication_error: bad token", "auth"),
    ("invalid api key", "auth"),
    ("unauthorized", "auth"),
    ("oauth token has expired", "auth"),
    ("your credit_balance is too low", "quota"),
    ("insufficient quota", "quota"),
    ("billing hard limit reached", "quota"),
])
def test_anbieter_fehler_aus_dem_text(msg, cat):
    assert classify(Exception(msg)) == cat


@pytest.mark.parametrize("exc", [
    httpx.ReadTimeout(""), httpx.ConnectTimeout(""), httpx.WriteTimeout(""),
    asyncio.TimeoutError(), TimeoutError("primary down"),
], ids=lambda e: type(e).__name__)
def test_timeouts(exc):
    assert classify(exc) == "timeout"


@pytest.mark.parametrize("exc", [
    CodexStreamStall("Codex-Stream steht"),
    httpx.ReadError(""), httpx.ConnectError(""), httpx.WriteError(""),
    httpx.RemoteProtocolError("Server disconnected"),
], ids=lambda e: type(e).__name__)
def test_verbindungsabbrueche(exc):
    assert classify(exc) == "stream_abort"


@pytest.mark.parametrize("msg", [
    "line 402, in foo",          # Zahl im Stacktrace ist kein Statuscode
    "invalid credentials",       # 'credentials' ist kein Key-Fehler
    "json decode error",
    "tool not found",
])
def test_kein_wechselgrund(msg):
    assert classify(ValueError(msg)) is None


def test_kategorien_mengen():
    assert PROVIDER_CATEGORIES == {"auth", "quota", "rate_limit", "overload"}
    assert SWITCH_CATEGORIES == PROVIDER_CATEGORIES | {"timeout", "stream_abort"}


def test_should_failover_bleibt_bei_anbieterfehlern():
    """Kompaktierung + bisherige Aufrufer: Verbindungsfehler wechseln dort weiter NICHT über diese Funktion."""
    assert should_failover(Exception("Error 429")) is True
    assert should_failover(httpx.ReadTimeout("")) is False
    assert should_failover(Exception("request timed out")) is False
