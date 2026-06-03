"""teamchat/presence.py — HH-native Presence (online = aktive teamchat-SSE-Verbindung).

Kein Matrix-Presence (das käme über den Sync-Loop, den Schicht 1 bewusst nicht hat).
Stattdessen ein Refcount pro User: jede offene `/rooms/{id}/stream`-Verbindung zählt;
fällt der Zähler auf 0, ist der User offline. Reines In-Memory, prozesslokal.
"""
from __future__ import annotations

import threading


class Presence:
    """Refcount aktiver SSE-Verbindungen pro User."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def connect(self, user_id: str) -> None:
        with self._lock:
            self._counts[user_id] = self._counts.get(user_id, 0) + 1

    def disconnect(self, user_id: str) -> None:
        with self._lock:
            remaining = self._counts.get(user_id, 0) - 1
            if remaining <= 0:
                self._counts.pop(user_id, None)
            else:
                self._counts[user_id] = remaining

    def online_users(self) -> set[str]:
        with self._lock:
            return set(self._counts)


# Prozessweiter Singleton — geteilt von der Stream-Route und dem /presence-Endpoint.
presence = Presence()
