"""Vault-Token: gleitend 15 min, max 8 h, an Nutzer und PIN-Generation gebunden (vault.md §4.3)."""
from __future__ import annotations

import pytest


def _t():
    from hydrahive.vault import tokens
    return tokens


def test_frischer_token_gilt(client):
    t = _t()
    tok = t.issue("u1", generation=1, now=1000.0)
    assert t.check(tok, "u1", generation=1, now=1000.0 + 60) is True


def test_nach_pause_gesperrt(client):
    t = _t()
    tok = t.issue("u1", generation=1, now=1000.0)
    assert t.check(tok, "u1", generation=1, now=1000.0 + t.IDLE_SECONDS - 1) is True
    assert t.check(tok, "u1", generation=1, now=1000.0 + t.IDLE_SECONDS + 1) is False


def test_gleitend_verlaengern(client):
    t = _t()
    tok = t.issue("u1", generation=1, now=1000.0)
    later = 1000.0 + t.IDLE_SECONDS - 10
    tok2 = t.refresh(tok, "u1", generation=1, now=later)
    assert tok2 and t.check(tok2, "u1", generation=1, now=later + t.IDLE_SECONDS - 10) is True


def test_harte_obergrenze_8_stunden(client):
    t = _t()
    tok = t.issue("u1", generation=1, now=0.0)
    now = 0.0
    while now < t.MAX_SECONDS - t.IDLE_SECONDS:
        now += t.IDLE_SECONDS - 5
        tok = t.refresh(tok, "u1", generation=1, now=now) or tok
    assert t.check(tok, "u1", generation=1, now=t.MAX_SECONDS + 1) is False
    assert t.refresh(tok, "u1", generation=1, now=t.MAX_SECONDS + 1) is None


def test_fremder_nutzer_oder_alte_generation(client):
    t = _t()
    tok = t.issue("u1", generation=1, now=1000.0)
    assert t.check(tok, "u2", generation=1, now=1001.0) is False
    assert t.check(tok, "u1", generation=2, now=1001.0) is False


@pytest.mark.parametrize("bad", ["", "abc", "a.b.c", None])
def test_kaputter_token(client, bad):
    assert _t().check(bad, "u1", generation=1, now=1.0) is False


def test_manipulierter_token(client):
    t = _t()
    tok = t.issue("u1", generation=1, now=1000.0)
    head, _, sig = tok.rpartition(".")
    forged = head + "." + ("A" if sig[0] != "A" else "B") + sig[1:]
    assert t.check(forged, "u1", generation=1, now=1001.0) is False
