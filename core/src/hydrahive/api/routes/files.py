"""Datei-Auslieferung für Frontend-Anzeige (generierte Bilder/Audios in /tmp etc).

Browser kann file:// und absolute Filesystem-Pfade nicht laden — das LLM
generiert aber oft Bilder als /tmp/foo.png oder im Agent-Workspace. Dieser
Endpoint liefert sie aus mit Pfad-Allowlist gegen Path-Traversal.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/files", tags=["files"])


def _allowed_roots() -> list[Path]:
    return [
        Path("/tmp").resolve(),
        settings.agents_dir.resolve(),
        settings.data_dir.resolve(),
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
def get_file(path: str = Query(..., min_length=1)) -> FileResponse:
    p = Path(path)
    if not p.is_absolute():
        raise coded(400, "path_must_be_absolute")
    if not _is_allowed(p):
        raise coded(403, "path_not_allowed")
    if not p.exists() or not p.is_file():
        raise coded(404, "file_not_found")
    mime, _ = mimetypes.guess_type(str(p))
    return FileResponse(str(p), media_type=mime or "application/octet-stream")
