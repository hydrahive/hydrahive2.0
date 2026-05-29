"""Best-effort Secret-Redaction für Transkript-Inhalte vor dem Sync.

Maskiert offensichtliche Geheimnis-Muster (API-Keys, Bearer-Tokens,
password/HH_PASS-Zuweisungen). Bewusst best-effort: ein Passwort in Prosa
ohne erkennbares Muster bleibt unmaskiert — keine Redaction-Garantie.
"""
from __future__ import annotations

import re

_REDACTED = "[redacted]"

# Muster ohne Gruppe → komplett ersetzen. Muster mit Gruppe(1) → Präfix behalten,
# Rest ersetzen (z.B. "Bearer " / "HH_PASS=" bleibt sichtbar, der Wert nicht).
_FULL = [
    re.compile(r"hhk_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub-Token (ghp_/gho_/ghu_/ghs_/ghr_)
]
_PREFIXED = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)((?:hh_pass|hh_api_key|password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)\S+"),
]


def redact_text(text: str) -> str:
    out = text
    for pat in _FULL:
        out = pat.sub(_REDACTED, out)
    for pat in _PREFIXED:
        out = pat.sub(lambda m: m.group(1) + _REDACTED, out)
    return out


def _redact_value(v):
    if isinstance(v, str):
        return redact_text(v)
    if isinstance(v, list):
        return [_redact_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _redact_value(x) for k, x in v.items()}
    return v


def redact_entries(entries: list[dict]) -> list[dict]:
    """Scrubbt `content` jedes Eintrags rekursiv. message_id/role/created_at unberührt."""
    return [{**e, "content": _redact_value(e.get("content"))} for e in entries]
