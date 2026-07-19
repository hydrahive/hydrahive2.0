"""Per-Key In-Memory Rate-Limit für unauthentifizierte Inbound-Endpoints
(Issue #180).

Sliding-Window-Zähler, analog zu lockout.py. Reset bei Backend-Restart ist
akzeptabel (Backstop gegen Kosten-DoS / Sample-Flooding, nicht das primäre
Auth-Gate). Schlüssel ist typischerweise '<endpoint>:<client-ip>'.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

WINDOW_SECONDS = 60
DEFAULT_LIMIT = 120
MAX_TRACKED_KEYS = 10_000

_lock = Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def check_rate(key: str, *, limit: int = DEFAULT_LIMIT, window: int = WINDOW_SECONDS) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). Zählt den Treffer nur, wenn erlaubt."""
    now = time.time()
    with _lock:
        if key not in _hits and len(_hits) >= MAX_TRACKED_KEYS:
            cutoff = now - window
            stale_keys = [tracked for tracked, hits in _hits.items() if not hits or hits[-1] <= cutoff]
            for stale in stale_keys:
                _hits.pop(stale, None)
            if len(_hits) >= MAX_TRACKED_KEYS:
                return False, max(1, window)
        entries = [t for t in _hits[key] if t > now - window]
        if len(entries) >= limit:
            _hits[key] = entries
            return False, max(1, int(entries[0] + window - now))
        entries.append(now)
        _hits[key] = entries
        return True, 0


def reset(key: str | None = None) -> None:
    """Counter leeren — `None` leert alle (für Tests / Restart-Semantik)."""
    with _lock:
        if key is None:
            _hits.clear()
        else:
            _hits.pop(key, None)
