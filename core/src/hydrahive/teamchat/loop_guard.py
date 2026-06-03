"""LoopGuard — Sliding-Window Circuit-Breaker gegen Bot-Echo-Schleifen.

Erkennt Bursts von Bot-Nachrichten innerhalb eines Zeitfensters und öffnet
einen Circuit Breaker für einen konfigurierbaren Cooldown.

Kein I/O, keine externen Abhängigkeiten — reines In-Memory-Modul.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class LoopGuard:
    """Sliding-Window Circuit-Breaker für Bot-Echo-Schleifen in Matrix-Räumen.

    Jeder Room hat einen unabhängigen Timestamp-Verlauf und Circuit-Zustand.
    Menschen-Nachrichten werden nie geblockt und berühren den Bot-Zähler nicht.
    """

    def __init__(
        self,
        threshold: int = 5,
        window_seconds: float = 30.0,
        cooldown_seconds: float = 300.0,
    ) -> None:
        # Sane Minima — schützt vor Fehlkonfiguration
        self.threshold = max(2, threshold)
        self.window_seconds = max(1.0, window_seconds)
        self.cooldown_seconds = max(1.0, cooldown_seconds)

        # room_id → sortierte Liste von Bot-Timestamps (monotonic)
        self._history: dict[str, list[float]] = {}
        # room_id → Zeitpunkt an dem der Circuit geöffnet wurde
        self._circuit_open: dict[str, float] = {}

    def check(self, room_id: str, is_bot: bool, *, now: float | None = None) -> bool:
        """Prüft ob eine Nachricht geblockt werden soll.

        Returns:
            True  → Nachricht blocken (Loop erkannt oder Circuit noch offen).
            False → Nachricht durchlassen.
        """
        now = now if now is not None else time.monotonic()

        if not is_bot:
            return False  # Menschen nie blocken

        # Circuit noch offen?
        if room_id in self._circuit_open:
            opened_at = self._circuit_open[room_id]
            if now - opened_at < self.cooldown_seconds:
                return True  # Cooldown läuft noch
            # Cooldown abgelaufen → Circuit schließen und Verlauf löschen
            logger.info(
                "LoopGuard: Circuit schließt wieder (room=%s, nach %.0fs Cooldown)",
                room_id,
                self.cooldown_seconds,
            )
            del self._circuit_open[room_id]
            self._history.pop(room_id, None)

        # Timestamp anhängen und veraltete Einträge entfernen
        history = self._history.setdefault(room_id, [])
        history.append(now)
        cutoff = now - self.window_seconds
        # Von vorne löschen bis alle verbleibenden Einträge im Fenster liegen
        while history and history[0] < cutoff:
            history.pop(0)

        # Threshold erreicht → Circuit öffnen
        if len(history) >= self.threshold:
            logger.warning(
                "LoopGuard: %d Bot-Nachrichten in %.0fs Fenster — "
                "Circuit Breaker ausgelöst (room=%s, %.0fs Cooldown)",
                len(history),
                self.window_seconds,
                room_id,
                self.cooldown_seconds,
            )
            self._circuit_open[room_id] = now
            return True

        return False
