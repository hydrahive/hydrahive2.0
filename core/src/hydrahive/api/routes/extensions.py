"""Extensions — App Manager: Liste, Install, Uninstall (nativ + Docker)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
import hydrahive.api.routes._extensions_runner as _runner
from hydrahive.api.routes._extensions_runner import (
    extension_status,
    load_manifests,
    stream_docker,
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


def _resolve_params(manifest: dict, user_params: dict[str, str]) -> dict[str, str]:
    """Füllt auto_generate-Felder auf wenn leer."""
    result = dict(user_params)
    for p in manifest.get("install_params", []):
        key = p["key"]
        auto = p.get("auto_generate", "")
        if auto and not result.get(key, "").strip():
            if auto.startswith("hex:"):
                length = int(auto.split(":")[1])
                result[key] = secrets.token_hex(length)
    return result


def _write_docker_credentials(manifest: dict, params: dict[str, str]) -> None:
    cred_dir = settings.config_dir / "extensions"
    cred_dir.mkdir(parents=True, exist_ok=True)
    cred_file = cred_dir / f"{manifest['id']}.credentials.json"

    fields = []
    docker = manifest.get("docker", {})
    open_url = docker.get("open_url", "")
    if open_url:
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
        fields.append({"key": "url", "label": "URL",
                       "value": f"http://{ip}{open_url}", "secret": False})

    for p in manifest.get("install_params", []):
        if p.get("auto_generate") and p.get("required") is False:
            continue  # kein Secret-Key im Credentials-Display
        val = params.get(p["key"], "")
        if not val:
            continue
        fields.append({
            "key": p["key"],
            "label": p["label"],
            "value": val,
            "secret": p.get("type") == "password",
        })

    payload = {
        "extension_id": manifest["id"],
        "extension_name": manifest["name"],
        "install_mode": "docker",
        "fields": fields,
    }
    cred_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    try:
        os.chmod(cred_file, 0o640)
    except Exception:
        pass


@router.post("/install-docker", dependencies=[Depends(require_admin)])
async def install_docker_engine() -> StreamingResponse:
    """Stellt sicher dass Docker läuft — installiert nur wenn nötig."""
    async def _generate():
        def _sudo(parts: list[str]) -> list[str]:
            return parts if os.getuid() == 0 else ["sudo", "-n"] + parts

        async def _run(cmd: list[str]) -> tuple[int, list[str]]:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            lines = []
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                lines.append(line.decode("utf-8", errors="replace").rstrip())
            await proc.wait()
            return proc.returncode, lines

        # Prüfen ob docker binary vorhanden
        rc, _ = await _run(["which", "docker"])
        docker_binary = rc == 0

        if not docker_binary:
            yield f"data: {json.dumps({'line': 'Docker nicht gefunden — starte Installation…'})}\n\n"
            proc = await asyncio.create_subprocess_exec(
                *_sudo(["/bin/bash", "-c", "curl -fsSL https://get.docker.com | sh"]),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                yield f"data: {json.dumps({'line': line.decode('utf-8', errors='replace').rstrip()})}\n\n"
            await proc.wait()
            if proc.returncode != 0:
                yield f"data: {json.dumps({'line': '[FEHLER] Docker-Installation fehlgeschlagen'})}\n\n"
                yield "data: {\"done\": true}\n\n"
                return
        else:
            yield f"data: {json.dumps({'line': 'Docker binary gefunden — prüfe Daemon…'})}\n\n"

        # Daemon starten + aktivieren
        yield f"data: {json.dumps({'line': 'Aktiviere und starte docker.service…'})}\n\n"
        rc, lines = await _run(_sudo(["systemctl", "enable", "--now", "docker"]))
        for l in lines:
            yield f"data: {json.dumps({'line': l})}\n\n"

        # Gruppe setzen damit hydrahive ohne sudo docker nutzen kann
        import pwd
        try:
            current_user = pwd.getpwuid(os.getuid()).pw_name if os.getuid() != 0 else "hydrahive"
            rc2, _ = await _run(_sudo(["usermod", "-aG", "docker", current_user]))
            if rc2 == 0:
                yield f"data: {json.dumps({'line': f'Benutzer {current_user} zur docker-Gruppe hinzugefügt'})}\n\n"
        except Exception:
            pass

        _runner._docker_available = None  # Cache zurücksetzen
        yield f"data: {json.dumps({'line': '[OK] Docker ist bereit'})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("", dependencies=[Depends(require_admin)])
async def list_extensions() -> list[dict]:
    manifests = load_manifests()
    return [await extension_status(m) for m in manifests]


@router.get("/credentials", dependencies=[Depends(require_admin)])
def list_credentials() -> list[dict]:
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
def validate_extension(ext_id: str, mode: str = "native") -> dict:
    manifest = _find_manifest(ext_id)
    errors = validate_manifest(manifest, mode)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/{ext_id}/install", dependencies=[Depends(require_admin)])
async def install_extension(ext_id: str, request: Request) -> StreamingResponse:
    manifest = _find_manifest(ext_id)

    user_params: dict[str, Any] = {}
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

    params = _resolve_params(manifest, {str(k): str(v) for k, v in user_params.items() if v})

    if mode == "docker":
        compose_rel = manifest["docker"]["compose_file"]
        compose_file = _scripts_base() / compose_rel
        success = False

        async def _generate_docker():
            nonlocal success
            async for line in stream_docker(compose_file, "up", env=params):
                yield f"data: {json.dumps({'line': line})}\n\n"
                if line.startswith("[OK]"):
                    success = True
            if success:
                try:
                    _write_docker_credentials(manifest, params)
                except Exception as e:
                    logger.error("Credentials schreiben fehlgeschlagen: %s", e)
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(_generate_docker(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    script = _scripts_base() / manifest["install_script"]

    async def _generate_native():
        async for line in stream_script(script, params):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate_native(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{ext_id}/uninstall", dependencies=[Depends(require_admin)])
async def uninstall_extension(ext_id: str, request: Request) -> StreamingResponse:
    manifest = _find_manifest(ext_id)

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
        compose_file = _scripts_base() / docker["compose_file"]

        async def _generate_docker_down():
            async for line in stream_docker(compose_file, "down"):
                yield f"data: {json.dumps({'line': line})}\n\n"
            cred_file = settings.config_dir / "extensions" / f"{manifest['id']}.credentials.json"
            if cred_file.exists():
                try:
                    cred_file.unlink()
                except Exception:
                    pass
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(_generate_docker_down(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    uninstall_rel = manifest.get("uninstall_script", "")
    if not uninstall_rel:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_uninstall_script")
    script = _scripts_base() / uninstall_rel
    if not script.exists():
        raise coded(status.HTTP_404_NOT_FOUND, "uninstall_script_missing")

    async def _generate_native():
        async for line in stream_script(script):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(_generate_native(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
