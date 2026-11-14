"""Kurzfassung + GitHub-Link-Erkennung für die Trace-Route des Agenten-Büros.

Spec agent-office.md §2 (Kurzfassung, kein Nutzdaten-Leck) und §8.2 (PR-/Issue-Link im Drawer,
reines Parsen auf vorhandenem Text — kein neuer GitHub-Call, keine neue Berechtigung nötig).
"""
from __future__ import annotations

import re

_SUMMARY_MAX_CHARS = 200
_GITHUB_LINK_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/(?:pull|issues)/\d+")


def _as_text(result: object) -> str:
    if isinstance(result, str):
        return result
    if result is None:
        return ""
    return str(result)


def result_summary(result: object) -> str:
    """Erste ~200 Zeichen des Tool-Ergebnisses — kein Volltext-Leck im Drawer."""
    text = _as_text(result).strip()
    return text[:_SUMMARY_MAX_CHARS]


def github_link(result: object) -> str | None:
    """Erster PR-/Issue-Link im Tool-Ergebnis, sonst None (Spec §8.2)."""
    match = _GITHUB_LINK_RE.search(_as_text(result))
    return match.group(0) if match else None
