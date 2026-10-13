"""Admin-API des System-Archivs (docs/specs/archiv-system.md, Etappe 1).

Nur lesen und Papierkorb leeren. Archiviert wird ab Etappe 2 beim Löschen.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.archive import catalog, trash
from hydrahive.archive.share import archive_share_enabled
from hydrahive.samba.manager import samba_status
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/archive", tags=["admin"], dependencies=[Depends(require_admin)])

TRASH_CONFIRM_WORD = "Papierkorb"


class TrashEmptyRequest(BaseModel):
    confirm: str = ""


def _read_samba_password() -> str:
    try:
        return settings.samba_password_file.read_text().strip()
    except OSError:
        return ""


@router.get("/status")
def archive_status() -> dict:
    s = samba_status()
    enabled = archive_share_enabled()
    return {
        "target": "local",
        "storage": catalog.usage(),
        "share": {
            "name": settings.archive_share_name,
            "enabled": enabled,
            "samba_installed": s["installed"],
            "samba_running": s["running"],
            "login": s["user"],
            "password": _read_samba_password() if s["installed"] and s["password_set"] else "",
        },
    }


@router.get("/entries")
def archive_entries(kind: str | None = None) -> dict:
    try:
        return {"entries": catalog.list_entries(kind=kind)}
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "archive_kind_invalid")


@router.post("/trash/empty")
def archive_trash_empty(req: TrashEmptyRequest) -> dict:
    if req.confirm != TRASH_CONFIRM_WORD:
        raise coded(status.HTTP_400_BAD_REQUEST, "archive_trash_confirm_required", word=TRASH_CONFIRM_WORD)
    try:
        freed = trash.empty_trash()
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "archive_trash_unsafe")
    except OSError as e:
        logger.warning("Papierkorb leeren fehlgeschlagen: %s", e)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "archive_trash_failed")
    return {"freed_bytes": freed}
