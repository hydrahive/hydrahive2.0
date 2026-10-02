"""Ausgefallene Suchanbieter aus einer SearXNG-Antwort lesen.

SearXNG meldet gesperrte Anbieter in ``unresponsive_engines`` als Liste von
``[name, grund]`` (z. B. ``["duckduckgo", "CAPTCHA"]``). Am 02.10.2026 waren
alle aktiven Anbieter gesperrt; die Websuche lieferte 0 Treffer, ohne dass es
jemand merkte (Spec docs/specs/websearch-blocked-engines.md).
"""
from __future__ import annotations

_MAX_REASON = 80


def unavailable_engines(data: object) -> list[dict[str, str]]:
    """Gültige Einträge als ``{engine, reason}``; Unbrauchbares wird übersprungen."""
    raw = data.get("unresponsive_engines") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        name, reason = entry
        if not isinstance(name, str) or not name.strip() or not isinstance(reason, str):
            continue
        out.append({"engine": name.strip(), "reason": reason.strip()[:_MAX_REASON]})
    return out


def describe(unavailable: list[dict[str, str]]) -> str:
    """„duckduckgo (CAPTCHA), brave (zu viele Anfragen)“."""
    return ", ".join(f"{u['engine']} ({u['reason']})" for u in unavailable)
