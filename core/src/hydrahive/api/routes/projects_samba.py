"""Samba-Toggle pro Projekt — opt-in Share."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.projects import config as project_config
from hydrahive.samba import disable_share, enable_share, is_share_enabled
from hydrahive.samba.manager import share_name_for

router = APIRouter(prefix="/api/projects", tags=["projects"])


class SambaToggle(BaseModel):
    enabled: bool


def _project_or_404(project_id: str, username: str, role: str) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    if role != "admin" and username not in p.get("members", []) and p.get("created_by") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")
    return p


@router.get("/{project_id}/samba")
def get_samba(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    enabled = bool(p.get("samba_enabled")) and is_share_enabled(project_id)
    return {
        "enabled": enabled,
        "share_name": share_name_for(project_id, p["name"]),
    }


@router.put("/{project_id}/samba")
def put_samba(
    project_id: str,
    req: SambaToggle,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    if req.enabled:
        ok, err = enable_share(project_id, p["name"])
        if not ok:
            sc = 400 if err == "samba_not_installed" else 500
            raise coded(sc, err or "samba_failed")
        project_config.update(project_id, samba_enabled=True)
    else:
        disable_share(project_id)
        project_config.update(project_id, samba_enabled=False)
    return {"ok": True, "enabled": req.enabled}
