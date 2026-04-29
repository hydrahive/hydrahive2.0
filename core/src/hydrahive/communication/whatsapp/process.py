"""Lifecycle der Node-Bridge: starten, stoppen, Shared-Secret verwalten.

Wenn Node nicht installiert ist oder `npm install` im Bridge-Verzeichnis
fehlt, wird die Bridge nicht gestartet — der Channel registriert sich
einfach nicht. Das System läuft trotzdem, im Frontend steht „Bridge
nicht verfügbar".
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

BRIDGE_DIR = Path(__file__).resolve().parent / "bridge"


def ensure_secret(secret_file: Path) -> str:
    """Lädt das Shared-Secret oder generiert eines beim ersten Aufruf."""
    if secret_file.exists():
        return secret_file.read_text().strip()
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    secret_file.write_text(token)
    secret_file.chmod(0o600)
    return token


async def _pump(stream: asyncio.StreamReader, level: int) -> None:
    while True:
        line = await stream.readline()
        if not line:
            return
        logger.log(level, "[wa-bridge] %s", line.decode(errors="replace").rstrip())


class BridgeProcess:
    def __init__(self, *, port: int, data_dir: Path, backend_url: str, secret: str):
        self.port = port
        self.data_dir = data_dir
        self.backend_url = backend_url
        self.secret = secret
        self._proc: asyncio.subprocess.Process | None = None
        self._pumps: list[asyncio.Task] = []

    @staticmethod
    def _has_node() -> bool:
        return shutil.which("node") is not None

    @staticmethod
    def _modules_installed() -> bool:
        return (BRIDGE_DIR / "node_modules" / "@whiskeysockets" / "baileys").exists()

    async def start(self) -> bool:
        if not self._has_node():
            logger.warning("Node.js fehlt — WhatsApp-Bridge wird nicht gestartet")
            return False
        if not self._modules_installed():
            logger.warning(
                "node_modules fehlen unter %s — bitte 'npm install' ausführen",
                BRIDGE_DIR,
            )
            return False
        self.data_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "HH_WA_DATA_DIR": str(self.data_dir),
            "HH_WA_BRIDGE_PORT": str(self.port),
            "HH_WA_BACKEND_URL": self.backend_url,
            "HH_WA_BRIDGE_SECRET": self.secret,
        })
        self._proc = await asyncio.create_subprocess_exec(
            "node", "index.js",
            cwd=str(BRIDGE_DIR),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._pumps = [
            asyncio.create_task(_pump(self._proc.stdout, logging.INFO)),
            asyncio.create_task(_pump(self._proc.stderr, logging.WARNING)),
        ]
        logger.info("WhatsApp-Bridge gestartet (PID %s, Port %s)", self._proc.pid, self.port)
        return True

    async def stop(self) -> None:
        if not self._proc or self._proc.returncode is not None:
            return
        self._proc.terminate()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._proc.kill()
            await self._proc.wait()
        for t in self._pumps:
            t.cancel()
        self._pumps = []
        logger.info("WhatsApp-Bridge gestoppt")
