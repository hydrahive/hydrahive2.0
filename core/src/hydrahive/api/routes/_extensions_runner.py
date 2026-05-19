"""Extensions — Manifest-Loading + Validation.

Status-Checks (Docker-Detection, Health) sind in `_extensions_status.py`,
Subprocess-Streamer in `_extensions_stream.py`. Dieses Modul re-exportiert
deren Public-API für externe Importer (extensions.py).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from hydrahive.api.routes._extensions_status import (
    _check_docker_marker,
    _check_docker_running,
    _check_health,
    _check_installed,
    _check_service_active,
    _docker_marker_path,
    docker_available,
    docker_binary_exists,
    extension_status,
    reset_docker_cache,
)
from hydrahive.api.routes._extensions_stream import stream_docker, stream_script
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_DANGEROUS_PATTERNS = [
    # rm -rf / oder rm -rf /toplevel (ein Level — kein /a/b/c-Pfad)
    r"rm\s+-rf\s+/[^/\s]*(?:\s|$)",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*bash",
    r"\bmkfs\b",
    r"dd\s+of=/dev/",
]

_MANIFEST_ORDER = [
    "gitea", "ollama", "codeserver", "searxng",
    "headscale", "vaultwarden", "pihole", "minecraft", "paperless-ngx",
]


def _manifests_dir() -> Path:
    if settings.extensions_manifests_dir.exists():
        return settings.extensions_manifests_dir
    return Path(__file__).resolve().parents[5] / "extensions" / "manifests"


def _scripts_base() -> Path:
    if settings.extensions_install_dir.parent.exists():
        return settings.extensions_install_dir.parent
    return Path(__file__).resolve().parents[5] / "extensions"


def load_manifests() -> list[dict]:
    d = _manifests_dir()
    if not d.exists():
        return []
    manifests: dict[str, dict] = {}
    for f in d.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            manifests[data["id"]] = data
        except Exception:
            logger.warning("Manifest %s konnte nicht geladen werden", f)
    ordered = [manifests.pop(k) for k in _MANIFEST_ORDER if k in manifests]
    ordered.extend(sorted(manifests.values(), key=lambda m: m.get("id", "")))
    return ordered


def validate_manifest(manifest: dict, mode: str = "native") -> list[str]:
    errors: list[str] = []
    if mode == "docker":
        docker = manifest.get("docker")
        if not docker:
            errors.append("Kein docker-Block im Manifest")
            return errors
        compose = _scripts_base() / docker.get("compose_file", "")
        if not compose.exists():
            errors.append(f"Compose-Datei nicht gefunden: {compose}")
        if not docker_binary_exists():
            errors.append("Docker ist nicht installiert")
        return errors

    for field in ("id", "name", "install_script", "installed_check"):
        if not manifest.get(field):
            errors.append(f"Pflichtfeld fehlt: {field}")
    script = _scripts_base() / manifest.get("install_script", "")
    if not script.exists():
        errors.append(f"Install-Script nicht gefunden: {script}")
    elif script.stat().st_size == 0:
        errors.append("Install-Script ist leer")
    else:
        content = script.read_text(errors="replace")
        for pat in _DANGEROUS_PATTERNS:
            if re.search(pat, content):
                errors.append(f"Gefährliches Pattern im Script: {pat}")
    return errors


# Legacy-Lesezugriff für externe Importer die `_runner._docker_*` direkt lesen.
def __getattr__(name: str):
    if name in ("_docker_available", "_docker_binary"):
        from hydrahive.api.routes import _extensions_status
        return getattr(_extensions_status, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
