"""Extensions — Status-Checks (Docker-Detection, Health-Checks, extension_status)."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import httpx

from hydrahive.settings import settings

logger = logging.getLogger(__name__)


# ── Docker-Detection ─────────────────────────────────────────────────────────

_docker_binary: bool | None = None
_docker_available: bool | None = None


def reset_docker_cache() -> None:
    """Setzt den Docker-Detection-Cache zurück — nach Install/Daemon-Start."""
    global _docker_binary, _docker_available
    _docker_binary = None
    _docker_available = None


def docker_binary_exists() -> bool:
    """Prüft nur ob das docker-Binary installiert ist."""
    global _docker_binary
    if _docker_binary is None:
        try:
            r = subprocess.run(["which", "docker"], capture_output=True, timeout=3)
            _docker_binary = r.returncode == 0
        except Exception:
            _docker_binary = False
    return _docker_binary


def docker_available() -> bool:
    """Prüft ob Docker-Daemon läuft und erreichbar ist."""
    global _docker_available
    if _docker_available is None:
        try:
            r = subprocess.run(
                ["docker", "info"], capture_output=True, timeout=5,
            )
            _docker_available = r.returncode == 0
        except Exception:
            _docker_available = False
    return _docker_available


# ── Status-Checks ─────────────────────────────────────────────────────────────

def _check_installed(manifest: dict) -> bool:
    check = manifest.get("installed_check", "")
    return bool(check and Path(check).exists())


def _check_docker_running(manifest: dict) -> bool:
    name = manifest.get("docker", {}).get("service_name", "")
    if not name:
        return False
    try:
        cmd = ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"]
        if os.getuid() != 0:
            cmd = ["sudo", "-n"] + cmd
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return name in r.stdout
    except Exception:
        return False


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


async def _check_health(manifest: dict, mode: str = "native") -> bool:
    docker = manifest.get("docker", {})
    url = (docker.get("health_url") if mode == "docker" else None) or manifest.get("health_url", "")
    if not url:
        return True
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(url)
            return r.status_code < 500
    except Exception:
        return False


def _docker_marker_path(manifest: dict) -> Path:
    return settings.config_dir / "extensions" / f".{manifest['id']}.docker_installed"


def _check_docker_marker(manifest: dict) -> bool:
    return _docker_marker_path(manifest).exists()


async def extension_status(manifest: dict) -> dict:
    docker_running = _check_docker_running(manifest)
    docker_marker = _check_docker_marker(manifest)
    # Für docker-only Extensions (preferred_mode=docker) zählt installed_check
    # nicht — das Data-Verzeichnis bleibt nach docker compose down erhalten.
    is_docker_only = manifest.get("preferred_mode") == "docker"
    native_mode = _check_installed(manifest) and not is_docker_only

    if docker_running or docker_marker:
        active = docker_running
        healthy = await _check_health(manifest, "docker") if docker_running else False
        install_mode = "docker"
    elif native_mode:
        active = _check_service_active(manifest)
        healthy = await _check_health(manifest, "native") if active else False
        install_mode = "native"
    else:
        active = False
        healthy = False
        install_mode = None

    # url_file: dynamische URL (z.B. macvlan-IP nach Install) überschreibt open_url
    open_url = manifest.get("open_url", "")
    url_file = manifest.get("url_file", "")
    if url_file:
        try:
            p = Path(url_file)
            if p.exists():
                open_url = p.read_text().strip()
        except Exception:
            pass

    return {
        **manifest,
        "open_url": open_url,
        "installed": docker_running or docker_marker or native_mode,
        "install_mode": install_mode,
        "active": active,
        "healthy": healthy,
        "docker_available": docker_binary_exists(),
    }
