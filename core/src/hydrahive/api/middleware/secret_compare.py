"""Konstant-zeitiger Secret-Vergleich (Issue #180).

Python `str.__ne__`/`__eq__` bricht beim ersten abweichenden Byte ab und ist
damit ein Timing-Side-Channel. `hmac.compare_digest` vergleicht in konstanter
Zeit. Fail-closed: ist kein Secret konfiguriert (leer/None), schlägt jeder
Vergleich fehl statt versehentlich durchzulassen.
"""
from __future__ import annotations

import hmac


def verify_secret(provided: str | None, expected: str | None) -> bool:
    if not expected:
        return False
    return hmac.compare_digest(provided or "", expected)
