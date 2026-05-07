"""Extensions — Manifest-Laden, Status-Checks, Script-Ausführung."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import AsyncIterator

import httpx

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/[^/]",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*bash",
    r"\bmkfs\b",
    r"dd\s+of=/dev/",
]

_MANIFEST_ORDER = [
    "gitea", "ollama", "codeserver", "searxng",
    "headscale", "vaultwarden", "pihole",
]


def _manifests_dir() -> Path:
    """Dev-Fallback: Projekt-Verzeichnis, Prod: settings.extensions_manifests_dir."""
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


def _check_installed(manifest: dict) -> bool:
    check = manifest.get("installed_check", "")
    return bool(check and Path(check).exists())


def _check_service_active(manifest: dict) -> bool:
    service = manifest.get("service", "")
    if not service:
        return False
    try:
        r = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=3,
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False


async def _check_health(manifest: dict) -> bool:
    url = manifest.get("health_url", "")
    if not url:
        return True
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(url)
            return r.status_code < 500
    except Exception:
        return False


async def extension_status(manifest: dict) -> dict:
    installed = _check_installed(manifest)
    active = _check_service_active(manifest) if installed else False
    healthy = await _check_health(manifest) if active else False
    return {**manifest, "installed": installed, "active": active, "healthy": healthy}


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
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


async def stream_script(script_path: Path, env: dict[str, str] | None = None) -> AsyncIterator[str]:
    import os
    full_env = {**os.environ, **(env or {})}
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", "/bin/bash", str(script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=full_env,
    )
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        yield line.decode("utf-8", errors="replace").rstrip("\n")
    await proc.wait()
    if proc.returncode != 0:
        yield f"[FEHLER] Script beendet mit Code {proc.returncode}"
    else:
        yield "[OK] Abgeschlossen"
