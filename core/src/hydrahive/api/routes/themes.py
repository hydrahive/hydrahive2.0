"""Admin-API für das Theme-System: Liste, Install, Update, Uninstall.

Spiegelt api/routes/modules.py — Themes sind über den Hub installierbar wie
Module, nur reines Frontend (kein Backend-Service/DB).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin
from hydrahive.themes import editor, hub_client, installer, registry

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


# ---------------------------------------------------------------------------
# Editor-API (Etappe 2): Template-HTML lesen/schreiben + Theme forken.
# ---------------------------------------------------------------------------

class TemplateBody(BaseModel):
    html: str = Field(default="", max_length=262_144)


class ForkBody(BaseModel):
    new_id: str = Field(min_length=1, max_length=64)
    new_name: str = Field(default="", max_length=120)


def _editor_call(fn, *args):
    """editor.* aufrufen und EditorError sauber in HTTP 400 übersetzen."""
    try:
        return fn(*args)
    except editor.EditorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{theme_id}/templates", dependencies=[Depends(require_admin)])
def list_theme_templates(theme_id: str) -> dict:
    routes = _editor_call(editor.list_templates, theme_id)
    return {"theme_id": theme_id, "routes": routes, "protected": registry.is_protected(theme_id)}


@router.get("/{theme_id}/templates/{route}", dependencies=[Depends(require_admin)])
def get_theme_template(theme_id: str, route: str) -> dict:
    html = _editor_call(editor.read_template, theme_id, route)
    return {"theme_id": theme_id, "route": route, "html": html}


@router.put("/{theme_id}/templates/{route}", dependencies=[Depends(require_admin)])
def put_theme_template(theme_id: str, route: str, body: TemplateBody) -> dict:
    _editor_call(editor.write_template, theme_id, route, body.html)
    return {"ok": True, "theme_id": theme_id, "route": route}


@router.delete("/{theme_id}/templates/{route}", dependencies=[Depends(require_admin)])
def delete_theme_template(theme_id: str, route: str) -> dict:
    _editor_call(editor.delete_template, theme_id, route)
    return {"ok": True, "theme_id": theme_id, "route": route}


@router.post("/{theme_id}/fork", dependencies=[Depends(require_admin)])
def fork_theme(theme_id: str, body: ForkBody) -> dict:
    return _editor_call(editor.fork_theme, theme_id, body.new_id, body.new_name)


@router.post("/{theme_id}/publish", dependencies=[Depends(require_admin)])
def publish_theme(theme_id: str) -> StreamingResponse:
    """Übernimmt editierte Templates ins laufende Frontend (Build + Restart)."""
    return _stream(installer.publish(theme_id))
