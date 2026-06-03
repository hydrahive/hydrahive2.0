"""Per-Agent tool_config: Secret-Maskierung für API + Preserve-on-Update.

Muster wie system_settings: Passwörter verlassen die API nie roh (`password=""`
+ `password_set`-Flag); ein leeres Passwort beim Schreiben heißt „nicht ändern".
"""
from __future__ import annotations

import copy

_SECRET_BLOCKS = ("smtp", "imap")


def mask(tool_config: dict | None) -> dict | None:
    """Kopie für API-Antworten: Passwort raus, `password_set`-Flag rein."""
    if not tool_config:
        return tool_config
    out = copy.deepcopy(tool_config)
    for block in _SECRET_BLOCKS:
        b = out.get(block)
        if isinstance(b, dict) and "password" in b:
            b["password_set"] = bool(b.get("password"))
            b["password"] = ""
    return out


def merge_secrets(existing: dict | None, incoming: dict) -> dict:
    """Merge fürs Speichern: leeres Passwort → bestehendes behalten; UI-Flag
    `password_set` wird nie persistiert."""
    existing = existing or {}
    merged = copy.deepcopy(incoming)
    for block in _SECRET_BLOCKS:
        b = merged.get(block)
        if not isinstance(b, dict):
            continue
        b.pop("password_set", None)
        if not b.get("password"):
            old = (existing.get(block) or {}).get("password", "")
            if old:
                b["password"] = old
    return merged
