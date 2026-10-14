"""Admin-API des System-Archivs (docs/specs/archiv-system.md, Etappe 1 + 2).

Status (richtet dabei Ordner und Freigabe ein), Einträge, Papierkorb leeren, Freigabe-Schalter,
Lösch-Vorschau und Lösch-Aufträge („Laufende Vorgänge“). Alles nur für Admins.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, StrictBool

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.archive import _plan, catalog, jobs, location, move_job, orphans, preview, setup, trash
from hydrahive.archive.share import SHARE_NAME, archive_share_enabled
from hydrahive.samba.manager import samba_status
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/archive", tags=["admin"], dependencies=[Depends(require_admin)])

TRASH_CONFIRM_WORD = "Papierkorb"


class TrashEmptyRequest(BaseModel):
    confirm: str = ""


class OrphanCleanupRequest(BaseModel):
    workspaces: list[str] = []
    agents: list[str] = []


class ShareSwitchRequest(BaseModel):
    enabled: StrictBool


def _read_samba_password() -> str:
    try:
        return settings.samba_password_file.read_text().strip()
    except OSError:
        return ""


def _mount_of(path: Path) -> str:
    """Einhängepunkt der Platte, auf der `path` liegt (oder läge) – für die Anzeige."""
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    p = p.resolve()
    while not os.path.ismount(p) and p != p.parent:
        p = p.parent
    return str(p)


@router.get("/status")
def archive_status() -> dict:
    result = setup.ensure_archive()
    s = samba_status()
    storage = catalog.usage()
    storage.update(is_default=location.is_default(), mount=_mount_of(Path(storage["path"])),
                   setup_error=result.get("error", ""))
    return {
        "target": "local",
        "storage": storage,
        "share": {
            "name": SHARE_NAME,
            "wanted": location.share_switch(),
            "paused_for_move": location.moving(),
            "enabled": archive_share_enabled(),
            "samba_installed": s["installed"],
            "samba_running": s["running"],
            "login": s["user"],
            "password": _read_samba_password() if s["installed"] and s["password_set"] else "",
        },
        "move": move_job.snapshot(),
        "jobs": jobs.list_jobs(),
    }


@router.get("/delete-preview")
def archive_delete_preview(kind: str, id: str) -> dict:
    try:
        return preview.preview(kind, id)
    except _plan.PlanError as e:
        if e.code == "not_found":
            raise coded(status.HTTP_404_NOT_FOUND, f"{kind}_not_found" if kind in _plan.t.KINDS else "not_found")
        raise coded(status.HTTP_400_BAD_REQUEST, e.code)


@router.get("/jobs")
def archive_jobs() -> dict:
    return jobs.list_jobs()


@router.put("/share")
def archive_share_switch(req: ShareSwitchRequest) -> dict:
    location.set_share_wanted(req.enabled)
    return setup.ensure_archive()


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


@router.get("/orphans")
def archive_orphans() -> dict:
    return orphans.scan()


@router.post("/orphans/cleanup", status_code=status.HTTP_202_ACCEPTED)
def archive_orphans_cleanup(req: OrphanCleanupRequest, admin: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    if not req.workspaces and not req.agents:
        raise coded(status.HTTP_400_BAD_REQUEST, "orphans_nothing_selected")
    try:
        return {"job_ids": orphans.submit_cleanup(workspaces=req.workspaces, agents=req.agents, actor=admin[0])}
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "orphans_invalid_id")
    except jobs.JobConflict:
        raise coded(status.HTTP_409_CONFLICT, "delete_in_progress")
