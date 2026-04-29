"""Strukturierte API-Errors mit Codes statt Strings.

Statt `HTTPException(status, "Ungültige Zugangsdaten")` (deutsche
Fehlermeldung schlägt im englischen UI durch und API-Konsumenten
müssen Strings parsen) liefert der Helper:

    {"detail": {"code": "invalid_credentials", "params": {...}}}

Das Frontend mappt den Code auf eine lokalisierte Nachricht via
i18next; API-Konsumenten (Bots, Skripte) prüfen den Code direkt.
Die Mapping-Tabelle der Codes lebt in
`frontend/src/i18n/locales/<lang>/errors.json`.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def coded(status_code: int, code: str, **params: Any) -> HTTPException:
    """Build an HTTPException whose `detail` is a code-based object.

    Usage:
        raise coded(401, "invalid_credentials")
        raise coded(404, "session_not_found", session_id=sid)
    """
    detail: dict[str, Any] = {"code": code}
    if params:
        detail["params"] = params
    return HTTPException(status_code=status_code, detail=detail)
