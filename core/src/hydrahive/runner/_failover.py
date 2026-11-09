"""LLM-Failover-Erkennung — bei Quota/Overload/Auth-Fehlern Modell wechseln.

Patterns mit Wort-Grenzen statt nackter Substring-Matches: '402' im
Stack-Trace einer Zeile (z.B. `line 402, in foo`) oder 'credit' in
'credentials' wäre sonst False-Positive.
"""
from __future__ import annotations

import re

_FAILOVER_PATTERNS = [
    re.compile(r"\b(?:401|402|429|529)\b"),
    re.compile(r"\bauthentication[ _]error\b"),
    re.compile(r"\binvalid (?:api )?(?:key|x-api-key)\b"),
    re.compile(r"\b(?:unauthorized|expired)\b"),
    # rate_limit_exceeded / rate-limited etc. ⇒ Suffix-Wort erlaubt, kein \b am Ende
    re.compile(r"\brate.?limit"),
    re.compile(r"\b(?:overloaded|quota|insufficient|capacity)\b"),
    re.compile(r"\bcredit_balance\b"),  # NICHT "credit" — matcht "credentials"
    re.compile(r"\b(?:billing|payment)\b"),
    re.compile(r"\boauth token has expired\b"),
]


def should_failover(exc: Exception) -> bool:
    """True wenn der Fehler einen Modellwechsel rechtfertigt."""
    err = str(exc).lower()
    return any(p.search(err) for p in _FAILOVER_PATTERNS)
