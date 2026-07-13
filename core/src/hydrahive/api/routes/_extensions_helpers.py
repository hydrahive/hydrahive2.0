"""Helper-Funktionen für die Extensions-Routes — Pfad/Manifest/Params/Credentials."""
from __future__ import annotations

import json
import logging
import os
import secrets
from pathlib import Path

from fastapi import status

from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._extensions_runner import load_manifests
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def scripts_base() -> Path:
    if settings.extensions_install_dir.parent.exists():
        return settings.extensions_install_dir.parent
    return Path(__file__).resolve().parents[5] / "extensions"


def find_manifest(ext_id: str) -> dict:
    for m in load_manifests():
        if m.get("id") == ext_id:
            return m
    raise coded(status.HTTP_404_NOT_FOUND, "extension_not_found")


def resolve_params(manifest: dict, user_params: dict[str, str]) -> dict[str, str]:
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


def write_docker_credentials(manifest: dict, params: dict[str, str]) -> None:
    cred_dir = settings.config_dir / "extensions"
    cred_dir.mkdir(parents=True, exist_ok=True)
    cred_file = cred_dir / f"{manifest['id']}.credentials.json"

    fields = []
    docker = manifest.get("docker", {})
    open_url = docker.get("open_url", "")
    if open_url:
        # Pattern (z.B. ":3001/") speichern — Frontend ergänzt window.location.hostname.
        # Kein socket.gethostbyname: löst die IP zum Install-Zeitpunkt auf und friert sie ein.
        fields.append({"key": "url", "label": "URL", "value": open_url, "secret": False})

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
    except OSError:
        pass  # Permission-Härtung best-effort (z.B. auf FS ohne chmod)
