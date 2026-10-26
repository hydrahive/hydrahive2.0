"""Samba-Toggle pro Projekt — opt-in Share."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.projects import config as project_config
from hydrahive.samba import disable_share, enable_share, is_share_enabled
from hydrahive.samba import manager as samba_manager
from hydrahive.samba.manager import share_name_for
from hydrahive.settings import settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


class SambaToggle(BaseModel):
    enabled: bool


def _project_or_404(project_id: str, username: str, role: str, required: str = "read") -> dict:
    """Projekt laden und Mindestrolle prüfen (read < write < admin, docs/specs/project-member-roles.md)."""
    from hydrahive.api.routes._project_route_helpers import check_project_access
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, username, role, required)
    return p


@router.get("/{project_id}/samba")
def get_samba(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    enabled = bool(p.get("samba_enabled")) and is_share_enabled(project_id)
    password = ""
    if settings.samba_password_file.exists():
        try:
            password = settings.samba_password_file.read_text().strip()
        except OSError:
            password = ""
    return {
        "enabled": enabled,
        "share_name": share_name_for(project_id, p["name"]),
        "user": samba_manager.share_user(),
        "password": password,
        # Mac: macOS-Dateifreigabe (smb://…, docs/plans/mac-file-sharing.md); Linux: Samba
        "platform": "mac" if samba_manager.is_mac() else "linux",
    }


@router.put("/{project_id}/samba")
def put_samba(
    project_id: str,
    req: SambaToggle,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth, required="write")
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
