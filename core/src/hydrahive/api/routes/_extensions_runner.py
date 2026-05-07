"""Extensions — Manifest-Laden, Status-Checks, Script- und Docker-Ausführung."""
from __future__ import annotations

import asyncio
import json
import logging
import os
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


# ── Docker-Detection ─────────────────────────────────────────────────────────

_docker_binary: bool | None = None
_docker_available: bool | None = None


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


# ── Manifest-Laden ────────────────────────────────────────────────────────────

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

    return {
        **manifest,
        "installed": docker_running or docker_marker or native_mode,
        "install_mode": install_mode,
        "active": active,
        "healthy": healthy,
        "docker_available": docker_binary_exists(),
    }


# ── Validierung ───────────────────────────────────────────────────────────────

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


# ── Ausführung ────────────────────────────────────────────────────────────────

async def stream_script(script_path: Path, env: dict[str, str] | None = None) -> AsyncIterator[str]:
    full_env = {**os.environ, **(env or {})}
    cmd = ["/bin/bash", str(script_path)] if os.getuid() == 0 else ["sudo", "-n", "/bin/bash", str(script_path)]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
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


async def stream_docker(
    compose_file: Path,
    action: str,
    env: dict[str, str] | None = None,
) -> AsyncIterator[str]:
    """action: 'up' oder 'down'"""
    import tempfile

    env_file: Path | None = None
    try:
        if action == "up":
            # Env-Variablen in temp .env-Datei schreiben — sudo strippt subprocess-env
            if env:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".env", delete=False, dir="/tmp"
                )
                for k, v in env.items():
                    tmp.write(f"{k}={v}\n")
                tmp.close()
                env_file = Path(tmp.name)
                os.chmod(env_file, 0o600)
                cmd = ["docker", "compose", "-f", str(compose_file),
                       "--env-file", str(env_file), "up", "-d", "--pull", "always"]
            else:
                cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d", "--pull", "always"]

            # sysctl für unprivilegierte Container-Ports setzen
            try:
                sysctl_cmd = ["sysctl", "-w", "net.ipv4.ip_unprivileged_port_start=0"]
                if os.getuid() != 0:
                    sysctl_cmd = ["sudo", "-n"] + sysctl_cmd
                subprocess.run(sysctl_cmd, capture_output=True, timeout=5)
            except Exception:
                pass
        elif action == "down":
            # Leere .env damit compose keine Warnings über fehlende Variablen wirft
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, dir="/tmp")
            tmp.close()
            env_file = Path(tmp.name)
            cmd = ["docker", "compose", "-f", str(compose_file),
                   "--env-file", str(env_file), "down", "--volumes", "--remove-orphans"]
        else:
            # start | stop | restart — kein volumes-Flag, kein env nötig
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, dir="/tmp")
            tmp.close()
            env_file = Path(tmp.name)
            cmd = ["docker", "compose", "-f", str(compose_file),
                   "--env-file", str(env_file), action]

        if os.getuid() != 0:
            cmd = ["sudo", "-n"] + cmd

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\n")
        await proc.wait()
        if proc.returncode != 0:
            yield f"[FEHLER] Docker beendet mit Code {proc.returncode}"
        else:
            yield "[OK] Abgeschlossen"
    finally:
        if env_file and env_file.exists():
            env_file.unlink(missing_ok=True)
