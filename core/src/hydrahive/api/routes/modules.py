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
    installed = [
        {
            "id": m.name,
            "loaded": m.loaded,
            "error": m.error,
            "version": m.manifest.version if m.manifest else None,
        }
        for m in REGISTRY.values()
    ]
    # Hub vor dem Listen pullen, damit "available" den echten Hub spiegelt.
    # read_hub_index() pullt nur bei FEHLENDEM Cache — ohne dies fröre die Liste
    # auf dem Stand des ersten Clones ein (neue Module würden nie auftauchen).
    # Netzwerk-/Hub-Fehler beim Refresh sind unkritisch → Fallback auf den Cache.
    try:
        hub_client.refresh()
    except Exception as exc:
        logger.warning("Modul-Hub-Refresh fehlgeschlagen, nutze Cache: %s", exc)
    try:
        available = hub_client.read_hub_index().get("modules", [])
    except Exception as exc:  # Hub unerreichbar → leere Liste, aber nicht still schlucken
        logger.warning("Modul-Hub-Index nicht abrufbar: %s", exc)
        available = []
    return {"installed": installed, "available": available}


def _stream(gen) -> StreamingResponse:
    def _events():
        for line in gen:
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/{module_id}/install", dependencies=[Depends(require_admin)])
def install_module(module_id: str) -> StreamingResponse:
    return _stream(installer.install(module_id))


@router.delete("/{module_id}", dependencies=[Depends(require_admin)])
def uninstall_module(module_id: str) -> StreamingResponse:
    return _stream(installer.uninstall(module_id))
