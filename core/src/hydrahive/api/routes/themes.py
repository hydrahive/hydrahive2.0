"""Admin-API für das Theme-System: Liste, Install, Update, Uninstall.

Spiegelt api/routes/modules.py — Themes sind über den Hub installierbar wie
Module, nur reines Frontend (kein Backend-Service/DB).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.themes import hub_client, installer, registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/themes", tags=["themes"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get("", dependencies=[Depends(require_admin)])
def list_themes() -> dict:
    installed = registry.list_installed()
    # Hub vor dem Listen pullen, damit "available" den echten Hub spiegelt.
    # Netzwerk-/Hub-Fehler sind unkritisch → Fallback auf den Cache.
    try:
        hub_client.refresh()
    except Exception as exc:
        logger.warning("Theme-Hub-Refresh fehlgeschlagen, nutze Cache: %s", exc)
    try:
        available = hub_client.read_hub_index().get("themes", [])
    except Exception as exc:
        logger.warning("Theme-Hub-Index nicht abrufbar: %s", exc)
        available = []
    return {"installed": installed, "available": available}


def _stream(gen) -> StreamingResponse:
    def _events():
        try:
            for line in gen:
                yield f"data: {json.dumps({'line': line})}\n\n"
            yield "data: {\"done\": true}\n\n"
        except Exception as exc:
            logger.exception("Theme-Operation fehlgeschlagen")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/{theme_id}/install", dependencies=[Depends(require_admin)])
def install_theme(theme_id: str) -> StreamingResponse:
    return _stream(installer.install(theme_id))


@router.post("/{theme_id}/update", dependencies=[Depends(require_admin)])
def update_theme(theme_id: str) -> StreamingResponse:
    return _stream(installer.update(theme_id))


@router.delete("/{theme_id}", dependencies=[Depends(require_admin)])
def uninstall_theme(theme_id: str) -> StreamingResponse:
    return _stream(installer.uninstall(theme_id))
