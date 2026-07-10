from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import user_preferences
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/api/me/preferences", tags=["me"])

VaultScope = Literal["private", "family", "business"]


class PreferencesOut(BaseModel):
    active_project_id: str | None = None
    active_media_project_id: str | None = None
    active_vault_scope: VaultScope = "private"
    cockpit_layout: dict[str, Any] = Field(default_factory=dict)


class PreferencesPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_project_id: str | None = None
    active_media_project_id: str | None = None
    active_vault_scope: VaultScope | None = None
    cockpit_layout: dict[str, Any] | None = None


def _visible_project_ids(username: str, role: str) -> set[str]:
    projects = project_config.list_all() if role == "admin" else project_config.list_for_user(username)
    return {p["id"] for p in projects}


def _sanitize_project_refs(username: str, role: str, prefs: dict[str, Any]) -> dict[str, Any]:
    visible = _visible_project_ids(username, role)
    for key in ("active_project_id", "active_media_project_id"):
        value = prefs.get(key)
        if value and value not in visible:
            prefs[key] = None
    return prefs


@router.get("", response_model=PreferencesOut)
def get_preferences(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict[str, Any]:
    username, role = auth
    prefs = user_preferences.get(username)
    return _sanitize_project_refs(username, role, prefs)


@router.patch("", response_model=PreferencesOut)
def patch_preferences(
    body: PreferencesPatch,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict[str, Any]:
    username, role = auth
    changes = body.model_dump(exclude_unset=True)
    visible = _visible_project_ids(username, role)
    for key in ("active_project_id", "active_media_project_id"):
        value = changes.get(key)
        if value and value not in visible:
            changes[key] = None
    prefs = user_preferences.patch(username, changes)
    return _sanitize_project_refs(username, role, prefs)
