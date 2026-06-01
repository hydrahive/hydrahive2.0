"""LLM-Failover-Entscheidung (Issue #205, kritischer Pfad).

should_failover entscheidet, ob bei einem Fehler auf das nächste Fallback-Modell
gewechselt wird. False-Positives (z.B. 'credentials' statt 'key') würden echte
Konfig-Fehler fälschlich als transient behandeln.
"""
from __future__ import annotations

import pytest

from hydrahive.runner._failover import should_failover


@pytest.mark.parametrize("msg", [
    "Error 429: Too Many Requests",
    "rate_limit_exceeded",
    "The model is overloaded, please retry",
    "authentication_error: bad token",
    "invalid api key",
    "unauthorized",
    "your credit_balance is too low",
    "HTTP 529 overloaded",
    "insufficient quota",
])
def test_should_failover_true(msg):
    assert should_failover(Exception(msg)) is True


@pytest.mark.parametrize("msg", [
    "connection reset by peer",
    "invalid credentials",          # 'credentials' != 'key' → kein Failover
    "json decode error",
    "tool not found",
    "unexpected end of stream",
])
def test_should_failover_false(msg):
    assert should_failover(Exception(msg)) is False
