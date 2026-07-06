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
    # Hub vor dem Listen pullen, damit "available" den echten Hub spiegelt.
    # read_hub_index() pullt nur bei FEHLENDEM Cache — ohne dies fröre die Liste
    # auf dem Stand des ersten Clones ein (neue Module würden nie auftauchen).
    # Netzwerk-/Hub-Fehler beim Refresh sind unkritisch → Fallback auf den Cache.
    # WICHTIG: erst refreshen, DANN available_version() lesen — sonst basiert die
    # Update-Erkennung auf einem veralteten Cache.
    try:
        hub_client.refresh()
    except Exception as exc:
        logger.warning("Modul-Hub-Refresh fehlgeschlagen, nutze Cache: %s", exc)

    installed = []
    for m in REGISTRY.values():
        inst_ver = m.manifest.version if m.manifest else None
        avail_ver = installer.available_version(m.name)
        installed.append({
            "id": m.name,
            "loaded": m.loaded,
            "error": m.error,
            "version": inst_ver,
            "available_version": avail_ver,
            "update_available": installer.is_update_available(inst_ver, avail_ver),
        })

    try:
        available = hub_client.read_hub_index().get("modules", [])
    except Exception as exc:  # Hub unerreichbar → leere Liste, aber nicht still schlucken
        logger.warning("Modul-Hub-Index nicht abrufbar: %s", exc)
        available = []
    return {"installed": installed, "available": available}


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
