"""Vault-PIN speichern, prüfen, zurücksetzen (docs/specs/vault.md §4.2, §4.4)."""
from __future__ import annotations

import pytest

from hydrahive.db.connection import db


def _pins():
    from hydrahive.vault import pins
    return pins


def test_ohne_pin_ist_nichts_gesetzt(client):
    assert _pins().is_set("u-ohne") is False
    assert _pins().verify("u-ohne", "123456") is False


def test_pin_setzen_und_pruefen(client):
    p = _pins()
    p.set_pin("u1", "123456")
    assert p.is_set("u1")
    assert p.verify("u1", "123456") is True
    assert p.verify("u1", "654321") is False
    assert p.verify("u1", "") is False


@pytest.mark.parametrize("bad", ["12345", "1234567890123", "12a456", " 123456", "", "１２３４５６"])
def test_pin_format_6_bis_12_ziffern(client, bad):
    with pytest.raises(_pins().PinFormatError):
        _pins().set_pin("u2", bad)


def test_pin_nie_im_klartext_gespeichert(client):
    _pins().set_pin("u3", "4711471")
    with db() as c:
        row = c.execute("SELECT * FROM vault_pins WHERE user_id = ?", ("u3",)).fetchone()
    assert row is not None
    assert "4711471" not in " ".join(str(v) for v in tuple(row))
    assert str(row["pin_hash"]).startswith("$2")             # bcrypt


def test_reset_entfernt_pin_und_erhoeht_generation(client):
    p = _pins()
    p.set_pin("u4", "123456")
    gen1 = p.generation("u4")
    p.reset("u4")
    assert p.is_set("u4") is False
    assert p.generation("u4") > gen1
    p.set_pin("u4", "999999")
    assert p.generation("u4") > gen1
    assert p.verify("u4", "123456") is False and p.verify("u4", "999999") is True


def test_pin_aendern_erhoeht_generation(client):
    p = _pins()
    p.set_pin("u5", "123456")
    g = p.generation("u5")
    p.set_pin("u5", "222222")
    assert p.generation("u5") > g


def test_bump_sperrt_ohne_pin_zu_loeschen(client):
    p = _pins()
    p.set_pin("u6", "123456")
    g = p.generation("u6")
    assert p.bump("u6") == g + 1
    assert p.is_set("u6") and p.verify("u6", "123456")
