from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone


def uuid7() -> str:
    """Time-sortable UUID v7 — RFC 9562.

    Layout: 48 bit unix-ms timestamp | 4 bit version | 12 bit rand_a |
    2 bit variant | 62 bit rand_b. Sorts chronologically by string,
    portable across DBs, no central counter needed.
    """
    ts_ms = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big")
    rand_b = int.from_bytes(os.urandom(8), "big")
    val = (ts_ms & 0xFFFFFFFFFFFF) << 80
    val |= 0x7 << 76
    val |= (rand_a & 0xFFF) << 64
    val |= 0x2 << 62
    val |= rand_b & 0x3FFFFFFFFFFFFFFF
    return str(uuid.UUID(int=val))


def now_iso() -> str:
    """ISO-8601 UTC timestamp with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
