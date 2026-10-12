"""Fehlversuche beim Entsperren (docs/specs/vault.md §4.3): 5 falsche PINs in 15 min → 15 min Pause.

In-Memory je user_id (wie api/middleware/lockout.py). Reset bei Neustart ist akzeptabel: der Angreifer braucht
ohnehin eine gültige Login-Sitzung.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

WINDOW_SECONDS = 15 * 60
THRESHOLD = 5

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)


def is_locked(user_id: str) -> tuple[bool, int]:
    now = time.time()
    with _lock:
        entries = [t for t in _attempts[user_id] if t > now - WINDOW_SECONDS]
        _attempts[user_id] = entries
        if len(entries) >= THRESHOLD:
            return True, max(1, int(entries[0] + WINDOW_SECONDS - now))
    return False, 0


def record_failure(user_id: str) -> None:
    with _lock:
        _attempts[user_id].append(time.time())


def reset(user_id: str) -> None:
    with _lock:
        _attempts.pop(user_id, None)


def clear() -> None:
    """Nur für Tests."""
    with _lock:
        _attempts.clear()
