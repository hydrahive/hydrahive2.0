"""Föderations-Katalog — Hub-Markierung + Einstellungen (docs/specs/federation-catalog.md).

Etappe 1: nur Datenmodell + Hub-Markierung, noch kein Versand. Diese Datei
ruft bewusst kein `send_signed`/`httpx` auf und startet keinen Hintergrund-Task.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.users import list_users
from hydrahive.api.routes.federation_peers import _peer_or_404, _public
from hydrahive.db import federation_catalog as catalog_db
from hydrahive.db import federation_peers as peers_db
from hydrahive.federation.catalog_changes import safe_refresh_gate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/federation", tags=["federation"])

_Admin = Annotated[tuple[str, str], Depends(require_admin)]


class HubBody(BaseModel):
    is_hub: bool


class CatalogAcceptBody(BaseModel):
    accept: bool


class CatalogSettingsBody(BaseModel):
    enabled: bool
    interval_seconds: int = Field(ge=60, le=3600)
    users: list[str] = Field(default_factory=list, max_length=200)
    excluded_projects: list[str] = Field(default_factory=list, max_length=500)

    # Kein Zeichen-Muster: Nutzernamen sind bei der Anlage frei (routes/users.py).
    # Maßgeblich ist die Prüfung gegen list_users() in put_catalog_settings.
    @field_validator("users")
    @classmethod
    def _check_users(cls, value: list[str]) -> list[str]:
        for u in value:
            if not (1 <= len(u) <= 128):
                raise ValueError(f"ungültiger Nutzername: {u}")
        return value

    @field_validator("excluded_projects")
    @classmethod
    def _check_projects(cls, value: list[str]) -> list[str]:
        for p in value:
            if not (1 <= len(p) <= 128):
                raise ValueError(f"ungültige Projekt-ID: {p}")
        return value


def _settings_response() -> dict:
    row = catalog_db.get_settings()
    hub = catalog_db.any_hub()
    accepting = catalog_db.any_accepting()
    return {
        "enabled": bool(row["enabled"]),
        "interval_seconds": row["interval_seconds"],
        "users": catalog_db.list_selected_users(),
        "excluded_projects": catalog_db.list_excluded_projects(),
        "hub": (
            {"id": hub["id"], "name": hub["name"], "status": hub["status"]} if hub else None
        ),
        "accepting_from": [{"id": p["id"], "name": p["name"]} for p in accepting],
        "last_push_at": row["last_push_at"],
        "last_ok_at": row["last_ok_at"],
        "last_full_at": row["last_full_at"],
        "last_error": row["last_error"],
    }


@router.put("/peers/{peer_id}/hub")
def set_hub(peer_id: str, body: HubBody, _: _Admin) -> dict:
    peer = _peer_or_404(peer_id)
    try:
        updated = catalog_db.set_hub(peer_id, body.is_hub)
    except catalog_db.CatalogConflict as c:
        raise coded(status.HTTP_409_CONFLICT, c.code, **c.params) from c
    if updated is None:  # zwischen Prüfung und Schreiben gelöscht
        raise coded(status.HTTP_404_NOT_FOUND, "peer_not_found")
    safe_refresh_gate()
    logger.info(
        "Föderations-Katalog: Hub-Markierung für Partner '%s' auf %s gesetzt",
        peer["name"], body.is_hub,
    )
    return _public(updated)


@router.put("/peers/{peer_id}/catalog")
def set_catalog_accept(peer_id: str, body: CatalogAcceptBody, _: _Admin) -> dict:
    peer = _peer_or_404(peer_id)
    try:
        updated = catalog_db.set_catalog_accept(peer_id, body.accept)
    except catalog_db.CatalogConflict as c:
        raise coded(status.HTTP_409_CONFLICT, c.code, **c.params) from c
    if updated is None:
        raise coded(status.HTTP_404_NOT_FOUND, "peer_not_found")
    logger.info(
        "Föderations-Katalog: Annahme von Partner '%s' auf %s gesetzt",
        peer["name"], body.accept,
    )
    return _public(updated)


@router.get("/catalog/settings")
def get_catalog_settings(_: _Admin) -> dict:
    return _settings_response()


@router.put("/catalog/settings")
def put_catalog_settings(body: CatalogSettingsBody, _: _Admin) -> dict:
    known = {u["username"] for u in list_users()}
    for u in body.users:
        if u not in known:
            raise coded(status.HTTP_400_BAD_REQUEST, "catalog_user_unknown", username=u)

    before_users = set(catalog_db.list_selected_users())
    before_projects = set(catalog_db.list_excluded_projects())

    catalog_db.update_settings(enabled=body.enabled, interval_seconds=body.interval_seconds)
    catalog_db.set_selected_users(body.users)
    catalog_db.set_excluded_projects(body.excluded_projects)

    after_users = set(body.users)
    after_projects = set(body.excluded_projects)
    if before_users != after_users or before_projects != after_projects:
        catalog_db.reset_all_cursors()
    safe_refresh_gate()

    return _settings_response()


@router.post("/catalog/sync-now")
async def catalog_sync_now(_: _Admin) -> dict:
    """Voller Abgleich sofort (Spec §API). Läuft unter derselben Sperre wie Timer
    und Event-Push. ``result``: ``ok`` · ``inactive`` (Sync aus/kein Hub, kein
    Netzverkehr) · Fehlercode des Laufs, z. B. ``peer_catalog_not_accepted``."""
    import asyncio

    from hydrahive.federation import catalog_sync

    result = await catalog_sync.sync(full=True, reason="manual")
    logger.info("Föderations-Katalog: Abgleich von Hand → %s", result)
    return {"result": result, "settings": await asyncio.to_thread(_settings_response)}
