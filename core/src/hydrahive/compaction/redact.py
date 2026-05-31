"""Secret-Redaction für serialisierten History-Text vor der Compaction.

Nutzt die zentrale SSOT in credentials.redaction — KEINE eigene Pattern-Liste.
Zwei divergierende Listen waren die Ursache des OpenRouter-Key-Leaks (Drift);
neue Provider/Patterns müssen genau an einer Stelle gepflegt werden.
"""
from __future__ import annotations

from hydrahive.credentials import redaction


def redact(text: str) -> str:
    if not isinstance(text, str):
        return text
    return redaction.redact_detected(text)


def add_pattern(pattern: str, replacement: str = "") -> None:
    """Plugins können eigene Patterns registrieren. Das Replacement-Label entfällt —
    die zentrale Redaction nutzt einen einheitlichen Platzhalter."""
    redaction.register_pattern(pattern)
