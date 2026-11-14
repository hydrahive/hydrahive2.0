"""LLM-Failover-Erkennung — Fehler einer Kategorie zuordnen, daraus Modellwechsel ableiten.

Kategorien (Spec agent-templates.md Kap. 8):
- auth, quota, rate_limit, overload: Anbieter-/Kontoproblem. Nächstes Modell, gestörtes Modell kurz sperren.
- timeout, stream_abort: Verbindung. Nach den Wiederholversuchen auf frischer Verbindung nächstes Modell.
- None: kein Wechselgrund (Konfig-/Programmfehler), der Fehler läuft durch.

Patterns mit Wort-Grenzen statt nackter Substring-Matches: '402' im Stack-Trace einer Zeile
(z.B. `line 402, in foo`) oder 'credit' in 'credentials' wäre sonst False-Positive.
"""
from __future__ import annotations

import asyncio
import re

import httpx

PROVIDER_CATEGORIES = frozenset({"auth", "quota", "rate_limit", "overload"})
SWITCH_CATEGORIES = PROVIDER_CATEGORIES | {"timeout", "stream_abort"}

# Reihenfolge zählt: der erste Treffer bestimmt die Kategorie.
_TEXT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("rate_limit", re.compile(r"\b429\b")),
    # rate_limit_exceeded / rate-limited etc. ⇒ Suffix-Wort erlaubt, kein \b am Ende
    ("rate_limit", re.compile(r"\brate.?limit")),
    ("overload", re.compile(r"\b529\b")),
    ("overload", re.compile(r"\b(?:overloaded|capacity)\b")),
    ("quota", re.compile(r"\b402\b(?!,)")),
    ("quota", re.compile(r"\b(?:quota|insufficient)\b")),
    ("quota", re.compile(r"\bcredit_balance\b")),  # NICHT "credit" — matcht "credentials"
    ("quota", re.compile(r"\b(?:billing|payment)\b")),
    ("auth", re.compile(r"\b401\b")),
    ("auth", re.compile(r"\bauthentication[ _]error\b")),
    ("auth", re.compile(r"\binvalid (?:api )?(?:key|x-api-key)\b")),
    ("auth", re.compile(r"\boauth token has expired\b")),
    ("auth", re.compile(r"\b(?:unauthorized|expired)\b")),
]

_TIMEOUT_TYPES: tuple[type[BaseException], ...] = (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError)
_ABORT_TYPES: tuple[type[BaseException], ...] = (
    httpx.ReadError, httpx.ConnectError, httpx.WriteError, httpx.RemoteProtocolError,
)


def _is_stream_stall(exc: BaseException) -> bool:
    # Lazy import: _codex_http zieht den Codex-Stack nach, _failover wird früh geladen (compaction).
    from hydrahive.runner._codex_http import CodexStreamStall
    return isinstance(exc, CodexStreamStall)


def classify(exc: BaseException) -> str | None:
    """Kategorie des Fehlers oder None, wenn kein Modellwechsel gerechtfertigt ist."""
    if isinstance(exc, _TIMEOUT_TYPES):
        return "timeout"
    if isinstance(exc, _ABORT_TYPES) or _is_stream_stall(exc):
        return "stream_abort"
    err = str(exc).lower()
    for category, pattern in _TEXT_PATTERNS:
        if pattern.search(err):
            return category
    return None


def should_failover(exc: Exception) -> bool:
    """True bei Anbieter-/Kontoproblemen. Verbindungsfehler zählen hier bewusst NICHT
    (Kompaktierung hat dafür eine eigene Regel, der Chat-Pfad nutzt `classify`)."""
    return classify(exc) in PROVIDER_CATEGORIES
