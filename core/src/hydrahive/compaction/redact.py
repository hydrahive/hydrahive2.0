from __future__ import annotations

import re

# Patterns für Secret-Redaction. Werden auf serialisierten History-Text angewendet
# bevor das LLM die Compaction-Anfrage sieht.
# Liste bewusst konservativ — falsche Positives sind besser als geleakte Keys.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-ant-(api03|oat01)-[A-Za-z0-9_\-]{20,}"), "sk-ant-***REDACTED***"),
    (re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),                 "sk-or-***REDACTED***"),
    (re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),               "sk-proj-***REDACTED***"),
    (re.compile(r"sk-[A-Za-z0-9]{40,}"),                       "sk-***REDACTED***"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"),                    "AIza***REDACTED***"),
    (re.compile(r"gsk_[A-Za-z0-9]{20,}"),                      "gsk_***REDACTED***"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"),                      "ghp_***REDACTED***"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),              "github_pat_***REDACTED***"),
    (re.compile(r"hf_[A-Za-z0-9]{20,}"),                       "hf_***REDACTED***"),
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", re.DOTALL),
                                                                "***REDACTED PRIVATE KEY***"),
    # Bearer-Header in serialisiertem Text
    (re.compile(r"(?i)Authorization:\s*Bearer\s+[A-Za-z0-9_\-\.]+"),
                                                                "Authorization: Bearer ***REDACTED***"),
]


def redact(text: str) -> str:
    if not isinstance(text, str):
        return text
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


def add_pattern(pattern: str, replacement: str) -> None:
    """Plugins können eigene Patterns registrieren."""
    _PATTERNS.append((re.compile(pattern), replacement))
