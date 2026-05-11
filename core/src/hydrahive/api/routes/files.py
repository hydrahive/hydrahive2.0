"""Datei-Auslieferung für Frontend-Anzeige (generierte Bilder/Audios in /tmp etc).

Browser kann file:// und absolute Filesystem-Pfade nicht laden — das LLM
generiert aber oft Bilder als /tmp/foo.png oder im Agent-Workspace. Dieser
Endpoint liefert sie aus mit Pfad-Allowlist gegen Path-Traversal.

Auth: Bearer-Header ODER Query-Param `token=` (für `<img src=...>` Tags
im Browser, die keinen Authorization-Header schicken können). Read-only,
nur Pfade unter `_allowed_roots()` werden ausgeliefert. Sensitive App-
Daten (sessions.db, wiki.db, whatsapp/Auth-State) sind NICHT erreichbar.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from hydrahive.api.middleware.auth import _decode, get_current_user_optional
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

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
        settings.tmp_dir.resolve(),
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
    token: str | None = Query(None),
    request: Request = None,
    user=Depends(get_current_user_optional),
) -> FileResponse:
    """File-Serving mit Auth via Bearer-Header ODER Query-Param `token=`.

    Frontend hängt `&token=<jwt>` an `<img src=...>`-URLs an, weil Browser
    bei `<img>`-Requests keinen Authorization-Header schicken können.
    """
    # Fallback: Bearer-Header fehlt → versuche Query-Token
    if not user and token:
        if token.startswith("hhk_"):
            from hydrahive.api.middleware.api_keys import verify as verify_key
            api_user = verify_key(token)
            if api_user:
                user = (api_user["username"], api_user["role"])
        else:
            # _decode raised 401 bei expired/invalid — durchreichen
            payload = _decode(token)
            user = (payload["sub"], payload["role"])

    if not user:
        raise coded(401, "authentication_required")

    p = Path(path)
    if not p.is_absolute():
        raise coded(400, "path_must_be_absolute")
    if not _is_allowed(p):
        raise coded(403, "path_not_allowed")
    if not p.exists() or not p.is_file():
        raise coded(404, "file_not_found")
    mime, _ = mimetypes.guess_type(str(p))
    return FileResponse(str(p), media_type=mime or "application/octet-stream")
