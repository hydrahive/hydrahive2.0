"""Best-effort sort_date: erstes YYYY-MM-DD / YYYY-MM / YYYY aus Freitext.

Akte-Datumsfelder sind unsauber ("2024-11-15 bis 2024-11-26", "2020",
"V.a. F43.x"). Für die Timeline brauchen wir ein sortierbares ISO-Datum.
"""
from __future__ import annotations

import re

_ISO = re.compile(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")


def to_sort_date(value: str | None) -> str | None:
    if not value:
        return None
    m = _ISO.search(value)
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2) or "01", m.group(3) or "01"
    return f"{y}-{mo}-{d}"
