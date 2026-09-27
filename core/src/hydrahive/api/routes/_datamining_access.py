"""Zugriffsregeln fürs Datamining (Security-Task ba5fd3c3).

Datamining spiegelt die Gespräche ALLER Nutzer. Lesen darf jeder nur seine
eigenen; Admins sehen alles und dürfen gezielt nach Nutzer filtern.
Aktionen mit Server-Wirkung (Embeddings zurücksetzen, Importe aus Dateien,
Logs, Git) sind Admin-Sache.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from hydrahive.api.middleware.auth import require_admin, require_auth

Auth = Annotated[tuple[str, str], Depends(require_auth)]
AdminAuth = Annotated[tuple[str, str], Depends(require_admin)]


def scoped_username(auth: tuple[str, str], requested: str | None = None) -> str | None:
    """Nutzerfilter für Lese-Abfragen.

    Nicht-Admins: immer der eigene Name — ein übergebener `requested` wird
    ignoriert. Admins: `requested` (oder None = alle Nutzer).
    """
    username, role = auth
    if role == "admin":
        return requested or None
    return username


def owns(auth: tuple[str, str], owner: str | None) -> bool:
    """Darf `auth` einen Datensatz mit Besitzer `owner` sehen?"""
    username, role = auth
    return role == "admin" or (owner is not None and owner == username)
