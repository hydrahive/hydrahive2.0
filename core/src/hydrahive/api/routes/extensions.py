"""Extensions — App Manager: Liste, Install, Uninstall (nativ + Docker)."""
from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._extensions_docker import install_docker_engine_stream
from hydrahive.api.routes._extensions_helpers import (
    find_manifest,
    resolve_params,
    scripts_base,
    write_docker_credentials,
)
from hydrahive.api.routes._extensions_runner import (
    _docker_marker_path,
    extension_status,
    load_manifests,
    stream_docker,
    stream_script,
    validate_manifest,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/extensions", tags=["extensions"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/install-docker", dependencies=[Depends(require_admin)])
async def install_docker_engine() -> StreamingResponse:
    """Stellt sicher dass Docker läuft — installiert nur wenn nötig."""
    return StreamingResponse(install_docker_engine_stream(),
                             media_type="text/event-stream", headers=_SSE_HEADERS)


@router.get("", dependencies=[Depends(require_admin)])
async def list_extensions() -> list[dict]:
    manifests = load_manifests()
    return [await extension_status(m) for m in manifests]


_FULL_URL_RE = re.compile(r"^https?://[^/]+(:\d+)?(/.*)?$")
_HOST_STRIP_RE = re.compile(r"^https?://[^/:]+")


def _normalize_cred_fields(fields: list[dict]) -> list[dict]:
    """Normalisiert URL-Felder: alte Einträge mit aufgelöster IP → Port-Pattern.

    Alte Credential-Dateien haben kein "key"-Feld — daher Matching auf jedes
    nicht-geheime Feld dessen Wert eine vollständige HTTP-URL ist.
    """
    result = []
    for f in fields:
        val = f.get("value") or ""
        if not f.get("secret") and isinstance(val, str) and _FULL_URL_RE.match(val):
            # "http://192.168.3.21:3001/" → ":3001/" + "key" ergänzen für Frontend
            stripped = _HOST_STRIP_RE.sub("", val) or "/"
            f = {**f, "key": "url", "value": stripped}
        result.append(f)
    return result


@router.get("/credentials", dependencies=[Depends(require_admin)])
def list_credentials() -> list[dict]:
    cred_dir = settings.config_dir / "extensions"
    if not cred_dir.exists():
        return []
    results = []
    for f in sorted(cred_dir.glob("*.credentials.json")):
        try:
            data = json.loads(f.read_text())
            data["fields"] = _normalize_cred_fields(data.get("fields") or [])
            results.append(data)
        except Exception:
            logger.warning("Credentials-Datei %s konnte nicht gelesen werden", f)
    return results


@router.get("/{ext_id}/validate", dependencies=[Depends(require_admin)])
def validate_extension(ext_id: str, mode: str = "native") -> dict:
    manifest = find_manifest(ext_id)
    errors = validate_manifest(manifest, mode)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/{ext_id}/install", dependencies=[Depends(require_admin)])
async def install_extension(ext_id: str, request: Request) -> StreamingResponse:
    manifest = find_manifest(ext_id)

    user_params: dict = {}
    mode = "native"
    try:
        body = await request.json()
        user_params = body.get("params", {})
        mode = body.get("mode", "native")
    except Exception:
        pass

    errors = validate_manifest(manifest, mode)
    if errors:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_manifest",
                    message="; ".join(errors))

    params = resolve_params(manifest, {str(k): str(v) for k, v in user_params.items() if v})

    if mode == "docker":
        compose_rel = manifest["docker"]["compose_file"]
        compose_file = scripts_base() / compose_rel
        success = False

        async def _generate_docker():
            nonlocal success
            async for line in stream_docker(compose_file, "up", env=params):
                yield f"data: {json.dumps({'line': line})}\n\n"
                if line.startswith("[OK]"):
                    success = True
            if success:
                try:
                    marker = _docker_marker_path(manifest)
                    marker.parent.mkdir(parents=True, exist_ok=True)
                    marker.touch()
                except Exception as e:
                    logger.error("Marker schreiben fehlgeschlagen: %s", e)
                try:
                    write_docker_credentials(manifest, params)
                except Exception as e:
                    logger.error("Credentials schreiben fehlgeschlagen: %s", e)
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(_generate_docker(), media_type="text/event-stream", headers=_SSE_HEADERS)

    script = scripts_base() / manifest["install_script"]

    async def _generate_native():
        async for line in stream_script(script, params):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate_native(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/{ext_id}/uninstall", dependencies=[Depends(require_admin)])
async def uninstall_extension(ext_id: str, request: Request) -> StreamingResponse:
    manifest = find_manifest(ext_id)

    mode = "native"
    try:
        body = await request.json()
        mode = body.get("mode", "native")
    except Exception:
        pass

    if mode == "docker":
        docker = manifest.get("docker")
        if not docker:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_docker_config")
        compose_file = scripts_base() / docker["compose_file"]

        async def _generate_docker_down():
            async for line in stream_docker(compose_file, "down"):
                yield f"data: {json.dumps({'line': line})}\n\n"
            for cleanup in [
                settings.config_dir / "extensions" / f"{manifest['id']}.credentials.json",
                _docker_marker_path(manifest),
            ]:
                try:
                    cleanup.unlink(missing_ok=True)
                except Exception:
                    pass
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(_generate_docker_down(), media_type="text/event-stream", headers=_SSE_HEADERS)

    uninstall_rel = manifest.get("uninstall_script", "")
    if not uninstall_rel:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_uninstall_script")
    script = scripts_base() / uninstall_rel
    if not script.exists():
        raise coded(status.HTTP_404_NOT_FOUND, "uninstall_script_missing")

    async def _generate_native():
        async for line in stream_script(script):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate_native(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/{ext_id}/docker/{action}", dependencies=[Depends(require_admin)])
async def docker_action(ext_id: str, action: str) -> StreamingResponse:
    """start | stop | restart für laufende Docker-Extensions."""
    if action not in ("start", "stop", "restart"):
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_action")
    manifest = find_manifest(ext_id)
    docker = manifest.get("docker")
    if not docker:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_docker_config")
    compose_file = scripts_base() / docker["compose_file"]

    async def _generate():
        async for line in stream_docker(compose_file, action):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream", headers=_SSE_HEADERS)
