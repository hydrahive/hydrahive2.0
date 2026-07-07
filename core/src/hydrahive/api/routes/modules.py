"""Admin-API für das Modulsystem: Liste, Install, Uninstall."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.modules import REGISTRY
from hydrahive.modules import hub_client
from hydrahive.modules import installer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/modules", tags=["modules"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get("", dependencies=[Depends(require_admin)])
def list_modules() -> dict:
    """Eine gemergte Liste aller Module (installiert + verfügbar).

    Jeder Eintrag trägt `installed` + Status. Der Hub-Index liefert alle bekannten
    Module; REGISTRY liefert den installierten Stand (überschreibt Name/Beschreibung
    mit dem tatsächlich installierten Manifest).
    """
    # Erst refreshen, DANN available_version/description lesen — sonst basiert die
    # Update-Erkennung auf einem veralteten Cache. Hub-Fehler sind unkritisch.
    try:
        hub_client.refresh()
    except Exception as exc:
        logger.warning("Modul-Hub-Refresh fehlgeschlagen, nutze Cache: %s", exc)
    try:
        hub_modules = hub_client.read_hub_index().get("modules", [])
    except Exception as exc:
        logger.warning("Modul-Hub-Index nicht abrufbar: %s", exc)
        hub_modules = []

    # id → Eintrag. Basis aus dem Hub (auch nicht-installierte Module).
    by_id: dict[str, dict] = {}
    for hm in hub_modules:
        mid = hm.get("id")
        if not mid:
            continue
        avail_ver = installer.available_version(mid)
        by_id[mid] = {
            "id": mid,
            "name": hm.get("name") or mid,
            "description": installer.available_description(mid),
            "installed": False,
            "loaded": False,
            "error": None,
            "version": None,
            "available_version": avail_ver,
            "update_available": False,
        }

    # Installierte Module drüberlegen (Name/Beschreibung aus dem echten Manifest).
    for m in REGISTRY.values():
        inst_ver = m.manifest.version if m.manifest else None
        avail_ver = installer.available_version(m.name)
        entry = by_id.get(m.name, {"id": m.name})
        entry.update({
            "id": m.name,
            "name": (m.manifest.name if m.manifest else None) or entry.get("name") or m.name,
            "description": (m.manifest.description if m.manifest else "")
                           or entry.get("description", ""),
            "installed": True,
            "loaded": m.loaded,
            "error": m.error,
            "version": inst_ver,
            "available_version": avail_ver,
            "update_available": installer.is_update_available(inst_ver, avail_ver),
        })
        by_id[m.name] = entry

    # Sortierung: installierte zuerst, dann alphabetisch nach Name.
    modules = sorted(
        by_id.values(),
        key=lambda e: (not e["installed"], e["name"].lower()),
    )
    return {"modules": modules}


@router.get("/update-count", dependencies=[Depends(require_admin)])
def module_update_count() -> dict:
    """Anzahl installierter Module mit verfügbarem Update — billig (kein git-pull).

    Für den Footer-Indikator gedacht. Liest available_version() aus dem
    VORHANDENEN Hub-Cache, ohne zu refreshen. Fehler → count 0 (nie werfen).
    """
    count = 0
    for m in REGISTRY.values():
        inst_ver = m.manifest.version if m.manifest else None
        avail_ver = installer.available_version(m.name)
        if installer.is_update_available(inst_ver, avail_ver):
            count += 1
    return {"count": count}


def _stream(gen) -> StreamingResponse:
    def _events():
        try:
            for line in gen:
                yield f"data: {json.dumps({'line': line})}\n\n"
            yield "data: {\"done\": true}\n\n"
        except Exception as exc:
            logger.exception("Modul-Operation fehlgeschlagen")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/{module_id}/install", dependencies=[Depends(require_admin)])
def install_module(module_id: str) -> StreamingResponse:
    return _stream(installer.install(module_id))


@router.post("/{module_id}/update", dependencies=[Depends(require_admin)])
def update_module(module_id: str) -> StreamingResponse:
    return _stream(installer.update(module_id))


@router.delete("/{module_id}", dependencies=[Depends(require_admin)])
def uninstall_module(module_id: str) -> StreamingResponse:
    return _stream(installer.uninstall(module_id))
