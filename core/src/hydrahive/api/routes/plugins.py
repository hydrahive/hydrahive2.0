"""Plugin-Routen — Admin-only.

GET  /api/plugins/hub          — verfügbare Plugins aus dem Hub-Index
GET  /api/plugins/installed    — lokal installierte Plugins mit Status
POST /api/plugins/install      — Plugin aus Hub kopieren + sofort laden
POST /api/plugins/uninstall    — Plugin-Verzeichnis entfernen
POST /api/plugins/update       — Hub-Cache pullen + Plugin neu kopieren
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.plugins import hub_client, installer
from hydrahive.plugins.registry import REGISTRY

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class PluginAction(BaseModel):
    name: str


@router.get("/hub")
def list_hub(_: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    try:
        hub_client.refresh()
        index = hub_client.read_hub_index()
    except hub_client.HubError as e:
        raise coded(
            status.HTTP_502_BAD_GATEWAY,
            "plugin_hub_unreachable",
            message=str(e),
        )
    return {
        "schema_version": index.get("schema_version"),
        "updated": index.get("updated"),
        "plugins": index.get("plugins") or [],
    }


@router.get("/installed")
def list_installed(_: Annotated[tuple[str, str], Depends(require_admin)]) -> list[dict]:
    out: list[dict] = []
    for plugin in REGISTRY.values():
        out.append({
            "name": plugin.name,
            "version": plugin.manifest.version if plugin.manifest else None,
            "description": plugin.manifest.description if plugin.manifest else None,
            "loaded": plugin.loaded,
            "error": plugin.error,
            "tools": [t.name for t in plugin.tools],
        })
    return out


@router.post("/install")
def install(
    body: PluginAction,
    _: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    try:
        hub_client.refresh()
        result = installer.install(body.name)
    except hub_client.HubError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, "plugin_hub_unreachable", message=str(e))
    except installer.InstallError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "plugin_install_failed", message=str(e))
    return {
        "name": result.name,
        "version": result.version,
        "restart_recommended": result.restart_recommended,
    }


@router.post("/uninstall")
def uninstall(
    body: PluginAction,
    _: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    try:
        result = installer.uninstall(body.name)
    except installer.InstallError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "plugin_uninstall_failed", message=str(e))
    return {
        "name": result.name,
        "restart_recommended": result.restart_recommended,
    }


@router.post("/update")
def update(
    body: PluginAction,
    _: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    try:
        result = installer.update(body.name)
    except hub_client.HubError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, "plugin_hub_unreachable", message=str(e))
    except installer.InstallError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "plugin_update_failed", message=str(e))
    return {
        "name": result.name,
        "version": result.version,
        "restart_recommended": result.restart_recommended,
    }
