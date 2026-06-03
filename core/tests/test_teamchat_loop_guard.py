"""LoopGuard Circuit-Breaker — TDD.

Alle Tests injizieren `now` explizit → kein sleep, vollständig deterministisch.
"""
from __future__ import annotations


# ---------------------------------------------------------------- Hilfsfunktion

def _guard(**kwargs):
    """Lazy import (settings.data_dir-Freeze-Gotcha)."""
    from hydrahive.teamchat.loop_guard import LoopGuard
    return LoopGuard(**kwargs)


# ---------------------------------------------------------------- Grundverhalten

def test_human_nachrichten_nie_geblockt():
    """Menschliche Nachrichten werden immer durchgelassen."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    for i in range(20):
        assert g.check("room1", is_bot=False, now=float(i)) is False


def test_human_beeinflussen_bot_zaehler_nicht():
    """Menschen-Nachrichten dürfen den Bot-Timestamp-Verlauf nicht berühren."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    # 100 Human-Nachrichten im Fenster
    for i in range(100):
        g.check("room1", is_bot=False, now=float(i))
    # Erste Bot-Nachricht darf nicht geblockt werden
    assert g.check("room1", is_bot=True, now=100.0) is False


# ---------------------------------------------------------------- Unter Schwelle

def test_unter_schwelle_nicht_geblockt():
    """threshold−1 Bot-Nachrichten im Fenster → kein Circuit."""
    g = _guard(threshold=5, window_seconds=30.0, cooldown_seconds=300.0)
    for i in range(4):          # 4 < 5
        assert g.check("room1", is_bot=True, now=float(i)) is False


# ---------------------------------------------------------------- Schwelle erreicht

def test_schwelle_loest_circuit_aus():
    """Genau threshold Bot-Nachrichten im Fenster → Circuit öffnet."""
    g = _guard(threshold=5, window_seconds=30.0, cooldown_seconds=300.0)
    for i in range(4):
        assert g.check("room1", is_bot=True, now=float(i)) is False
    # 5. Nachricht → Trip
    assert g.check("room1", is_bot=True, now=4.0) is True


def test_circuit_offen_blockiert_folgenachrichten():
    """Solange Cooldown läuft, werden weitere Bot-Nachrichten geblockt."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    # Circuit auslösen
    for i in range(3):
        g.check("room1", is_bot=True, now=float(i))
    # Mitten im Cooldown
    assert g.check("room1", is_bot=True, now=30.0) is True
    assert g.check("room1", is_bot=True, now=59.9) is True


# ---------------------------------------------------------------- Cooldown abgelaufen

def test_nach_cooldown_wieder_erlaubt():
    """Nach Ablauf des Cooldowns darf der Bot wieder schreiben."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    opened_at = 5.0
    for i in range(3):
        g.check("room1", is_bot=True, now=float(i))
    # Exakt cooldown_seconds nach opened_at → wieder offen
    assert g.check("room1", is_bot=True, now=opened_at + 60.0) is False


def test_nach_cooldown_zaehler_reset():
    """Nach Cooldown wird der Timestamp-Verlauf gecleart; threshold−1 Nachrichten
    direkt danach dürfen wieder nicht geblockt werden."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    for i in range(3):
        g.check("room1", is_bot=True, now=float(i))
    # Cooldown abgelaufen
    t_after = 2.0 + 60.0  # opened_at = 2.0 (3. Nachricht), cooldown = 60
    assert g.check("room1", is_bot=True, now=t_after) is False
    # Noch eine → immer noch unter Schwelle (nur 2 bisher in neuem Fenster)
    assert g.check("room1", is_bot=True, now=t_after + 1.0) is False


# ---------------------------------------------------------------- Sliding Window

def test_nachrichten_ausserhalb_fenster_zaehlen_nicht():
    """Nachrichten die älter als window_seconds sind, zählen nicht.
    Das ist der HH1-Bug den wir beheben: deque(maxlen=N) ohne Zeitfenster
    würde 3 Nachrichten über 3 Tage verteilt fälschlicherweise trippen."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=300.0)
    # Nachrichten mit großem Zeitabstand (je window+1 Sekunden auseinander)
    g.check("room1", is_bot=True, now=0.0)
    g.check("room1", is_bot=True, now=11.0)   # erste ist jetzt außerhalb
    result = g.check("room1", is_bot=True, now=22.0)  # zweite auch außerhalb
    # Nur die letzte liegt im Fenster → unter Schwelle
    assert result is False


def test_sliding_window_burst_loest_aus():
    """Burst innerhalb des Fensters → Trip."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=300.0)
    g.check("room1", is_bot=True, now=0.0)
    g.check("room1", is_bot=True, now=1.0)
    # Dritte Nachricht noch im Fenster
    assert g.check("room1", is_bot=True, now=2.0) is True


# ---------------------------------------------------------------- Room-Isolation

def test_rooms_unabhaengig():
    """Zwei Rooms beeinflussen einander nicht."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    # room1 trippen
    for i in range(3):
        g.check("room1", is_bot=True, now=float(i))
    # room2 muss unbeeinflusst sein
    assert g.check("room2", is_bot=True, now=10.0) is False


def test_circuit_offen_room1_nicht_room2():
    """Circuit in room1 offen → room2 kann weiterhin senden."""
    g = _guard(threshold=3, window_seconds=10.0, cooldown_seconds=60.0)
    for i in range(3):
        g.check("room1", is_bot=True, now=float(i))
    # room1 geblockt, room2 frei
    assert g.check("room1", is_bot=True, now=5.0) is True
    assert g.check("room2", is_bot=True, now=5.0) is False


# ---------------------------------------------------------------- Clamp-Verhalten

def test_clamp_threshold_mindest_2():
    """threshold < 2 wird auf 2 geclampt."""
    g = _guard(threshold=1, window_seconds=10.0, cooldown_seconds=60.0)
    assert g.threshold == 2


def test_clamp_window_mindest_1():
    """window_seconds < 1.0 wird auf 1.0 geclampt."""
    g = _guard(threshold=5, window_seconds=0.1, cooldown_seconds=60.0)
    assert g.window_seconds == 1.0


def test_clamp_cooldown_mindest_1():
    """cooldown_seconds < 1.0 wird auf 1.0 geclampt."""
    g = _guard(threshold=5, window_seconds=10.0, cooldown_seconds=0.0)
    assert g.cooldown_seconds == 1.0
