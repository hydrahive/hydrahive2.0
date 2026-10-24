"""uuid7 bleibt innerhalb einer Millisekunde in Reihenfolge (Task 4e5eaba5,
docs/specs/uuid7-reihenfolge.md). Vorher war rand_a zufällig → Sortierung nach
ID innerhalb derselben Millisekunde war Zufall (Wackeltest im Compute-Protokoll)."""
from __future__ import annotations

import uuid

import pytest

from hydrahive.db import _utils


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch):
    """Feste Uhr in Millisekunden; der Test stellt sie per clock.ms ein."""
    class Clock:
        ms = 1_792_000_000_000
    c = Clock()
    monkeypatch.setattr(_utils.time, "time", lambda: c.ms / 1000)
    monkeypatch.setattr(_utils, "_last_ms", 0, raising=False)
    monkeypatch.setattr(_utils, "_last_seq", 0, raising=False)
    return c


def _ts_ms(u: str) -> int:
    return uuid.UUID(u).int >> 80


def test_gleiche_millisekunde_aufsteigend(clock) -> None:
    ids = [_utils.uuid7() for _ in range(1000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 1000


def test_neue_millisekunde_aufsteigend(clock) -> None:
    a = _utils.uuid7()
    clock.ms += 1
    b = _utils.uuid7()
    assert a < b
    assert _ts_ms(b) == clock.ms


def test_zaehler_beginnt_je_millisekunde_unten(clock) -> None:
    """Start der Millisekunde liegt in der unteren Hälfte → Platz für ≥ 2048
    weitere IDs. 20 Millisekunden, damit ein Zufallsstart über 0x7FF sicher auffiele."""
    for _ in range(20):
        clock.ms += 1
        b = uuid.UUID(_utils.uuid7()).int
        assert (b >> 64) & 0xFFF < 0x800


def test_uhr_geht_zurueck_trotzdem_aufsteigend(clock) -> None:
    a = _utils.uuid7()
    clock.ms -= 5_000
    b = _utils.uuid7()
    assert a < b


def test_zaehler_ueberlauf_zieht_zeit_weiter(clock) -> None:
    ids = [_utils.uuid7() for _ in range(5000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 5000
    assert _ts_ms(ids[-1]) > clock.ms


def test_format_version_und_variante(clock) -> None:
    u = uuid.UUID(_utils.uuid7())
    assert u.version == 7
    assert u.variant == uuid.RFC_4122
    assert _ts_ms(str(u)) == clock.ms


def test_zufallsteil_bleibt_zufaellig(clock) -> None:
    lows = {uuid.UUID(_utils.uuid7()).int & ((1 << 62) - 1) for _ in range(200)}
    assert len(lows) == 200


def test_nach_ueberlauf_zaehler_wieder_unten(clock) -> None:
    """Nach dem Überlauf beginnt die nächste Millisekunde mit Zähler 0 und hat
    wieder Platz für viele IDs (nicht sofort erneuter Überlauf)."""
    ids = [_utils.uuid7() for _ in range(4097)]
    after = [i for i in ids if _ts_ms(i) == clock.ms + 1]
    assert after, "Überlauf muss in die nächste Millisekunde führen"
    first_seq = (uuid.UUID(after[0]).int >> 64) & 0xFFF
    assert first_seq == 0
