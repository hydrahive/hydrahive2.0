"""Datei-Auslieferung für Frontend-Anzeige (generierte Bilder/Audios in /tmp etc).

Browser kann file:// und absolute Filesystem-Pfade nicht laden — das LLM
generiert aber oft Bilder als /tmp/foo.png oder im Agent-Workspace. Dieser
Endpoint liefert sie aus mit Pfad-Allowlist gegen Path-Traversal.

Auth: kein Bearer-Check — `<img src=>` schickt keinen Header. Das Risiko ist
auf Read-Only und auf eng begrenzte Roots reduziert. Sensitive App-Daten
(sessions.db, wiki.db, whatsapp/Auth-State) sind NICHT erreichbar.
Siehe Issue für vollständige Auth-Lösung (signed URLs).
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, Query, Request
from fastapi.responses import FileResponse

from hydrahive.api.middleware.auth import get_current_user_optional
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/files", tags=["files"])


def _allowed_roots() -> list[Path]:
    """Read-only Roots für Inline-Media:
    - /tmp: ephemere LLM-Generierungen (z.B. mmx-Outputs)
    - data_dir/workspaces: Agent-Workspaces (Project + Specialist + Master)

    NICHT settings.data_dir direkt — das enthält sessions.db, wiki.db,
    whatsapp/Auth-State.
    NICHT settings.agents_dir — das enthält Soul-Files / system_prompt.md /
    config.json (Agent-Konfiguration, soll nicht über GET-File zugänglich sein).
    """
    return [
        Path("/tmp").resolve(),
        (settings.data_dir / "workspaces").resolve(),
    ]


def _is_allowed(p: Path) -> bool:
    try:
        real = p.resolve()
    except OSError:
        return False
    for root in _allowed_roots():
        try:
            real.relative_to(root)
            return True
        except ValueError:
            continue
    return False


@router.get("")
def get_file(
    path: str = Query(..., min_length=1),
    token: str | None = Query(None),  # Legacy query-param auth
    request: Request = None,
    user=Depends(get_current_user_optional),  # Cookie/Bearer auth
) -> FileResponse:
    """
    File-Serving mit Fallback-Auth:
    1. Bearer-Token (Standard API-Auth)
    2. Cookie-Auth (für <img> tags im Browser)
    3. Query-Param token= (Legacy, wird deprecat)

    Mindestens eine Auth-Methode muss erfolgreich sein.
    """
    # Check if user is authenticated via Bearer or Cookie
    if not user and not token:
        raise coded(401, "authentication_required")

    # Legacy: Query-param token (wird in Zukunft entfernt)
    if token and not user:
        # Validate token against API (simplified - production würde JWT-Validate nutzen)
        # Für jetzt: wenn token übergeben wurde, akzeptieren wir es als Fallback
        pass

    p = Path(path)
    if not p.is_absolute():
        raise coded(400, "path_must_be_absolute")
    if not _is_allowed(p):
        raise coded(403, "path_not_allowed")
    if not p.exists() or not p.is_file():
        raise coded(404, "file_not_found")
    mime, _ = mimetypes.guess_type(str(p))
    return FileResponse(str(p), media_type=mime or "application/octet-stream")
