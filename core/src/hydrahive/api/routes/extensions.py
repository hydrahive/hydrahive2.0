"""Extensions — App Manager: Liste, Install, Uninstall."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._extensions_runner import (
    extension_status,
    load_manifests,
    stream_script,
    validate_manifest,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/extensions", tags=["extensions"])


def _scripts_base() -> Path:
    if settings.extensions_install_dir.parent.exists():
        return settings.extensions_install_dir.parent
    return Path(__file__).resolve().parents[5] / "extensions"


def _find_manifest(ext_id: str) -> dict:
    for m in load_manifests():
        if m.get("id") == ext_id:
            return m
    raise coded(status.HTTP_404_NOT_FOUND, "extension_not_found")


@router.get("", dependencies=[Depends(require_admin)])
async def list_extensions() -> list[dict]:
    manifests = load_manifests()
    return [await extension_status(m) for m in manifests]


@router.get("/credentials", dependencies=[Depends(require_admin)])
def list_credentials() -> list[dict]:
    """Alle gespeicherten Extension-Zugangsdaten aus /etc/hydrahive2/extensions/*.credentials.json."""
    cred_dir = settings.config_dir / "extensions"
    if not cred_dir.exists():
        return []
    results = []
    for f in sorted(cred_dir.glob("*.credentials.json")):
        try:
            data = json.loads(f.read_text())
            results.append(data)
        except Exception:
            logger.warning("Credentials-Datei %s konnte nicht gelesen werden", f)
    return results


@router.get("/{ext_id}/validate", dependencies=[Depends(require_admin)])
def validate_extension(ext_id: str) -> dict:
    manifest = _find_manifest(ext_id)
    errors = validate_manifest(manifest)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/{ext_id}/install", dependencies=[Depends(require_admin)])
async def install_extension(ext_id: str, request: Request) -> StreamingResponse:
    manifest = _find_manifest(ext_id)
    errors = validate_manifest(manifest)
    if errors:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_manifest",
                    message="; ".join(errors))

    params: dict[str, Any] = {}
    try:
        body = await request.json()
        params = body.get("params", {})
    except Exception:
        pass

    script = _scripts_base() / manifest["install_script"]
    env = {str(k): str(v) for k, v in params.items() if v is not None}

    async def _generate():
        async for line in stream_script(script, env):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{ext_id}/uninstall", dependencies=[Depends(require_admin)])
async def uninstall_extension(ext_id: str) -> StreamingResponse:
    manifest = _find_manifest(ext_id)
    uninstall_rel = manifest.get("uninstall_script", "")
    if not uninstall_rel:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_uninstall_script")

    script = _scripts_base() / uninstall_rel
    if not script.exists():
        raise coded(status.HTTP_404_NOT_FOUND, "uninstall_script_missing")

    async def _generate():
        async for line in stream_script(script):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
