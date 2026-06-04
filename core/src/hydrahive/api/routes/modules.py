"""Admin-API für das Modulsystem: Liste, Install, Uninstall."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.modules import REGISTRY
from hydrahive.modules import hub_client
from hydrahive.modules import installer

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
    try:
        available = hub_client.read_hub_index().get("modules", [])
    except Exception:
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
