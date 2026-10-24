from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, timezone


# Monotonie je Prozess (RFC 9562 §6.2, Methode 1): rand_a ist ein Zähler
# innerhalb derselben Millisekunde. Vorher zufällig → IDs derselben ms in
# zufälliger Reihenfolge, Sortierung „created_at, id" wackelte (Task 4e5eaba5).
_SEQ_MAX = 0xFFF
_lock = threading.Lock()
_last_ms = 0
_last_seq = 0


def uuid7() -> str:
    """Time-sortable UUID v7 — RFC 9562.

    Layout: 48 bit unix-ms timestamp | 4 bit version | 12 bit rand_a |
    2 bit variant | 62 bit rand_b. Sorts chronologically by string,
    portable across DBs, no central counter needed.

    rand_a ist ein Zähler je Millisekunde (Start zufällig in der unteren
    Hälfte), damit IDs eines Prozesses streng aufsteigen – auch bei
    gleicher Millisekunde, Zählerüberlauf oder zurückgehender Uhr.
    rand_b bleibt zufällig (Eindeutigkeit, nicht erratbar).
    """
    global _last_ms, _last_seq
    with _lock:
        ts_ms = int(time.time() * 1000)
        if ts_ms > _last_ms:
            seq = int.from_bytes(os.urandom(2), "big") & 0x7FF
        else:
            ts_ms = _last_ms
            seq = _last_seq + 1
            if seq > _SEQ_MAX:
                ts_ms += 1
                seq = 0
        _last_ms, _last_seq = ts_ms, seq
    rand_b = int.from_bytes(os.urandom(8), "big")
    val = (ts_ms & 0xFFFFFFFFFFFF) << 80
    val |= 0x7 << 76
    val |= seq << 64
    val |= 0x2 << 62
    val |= rand_b & 0x3FFFFFFFFFFFFFFF
    return str(uuid.UUID(int=val))


def now_iso() -> str:
    """ISO-8601 UTC timestamp with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
