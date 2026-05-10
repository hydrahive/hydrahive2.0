"""Tailscale-Binary nachträglich installieren via Installer-Modul.

Ruft `sudo -n bash <repo>/installer/modules/80-tailscale.sh`. Die NOPASSWD-
sudoers für /bin/bash existiert bereits aus 50-systemd.sh (Extensions-
Manager). Daher kein zusätzlicher sudoers-Eintrag nötig.

Das Modul ist idempotent (`command -v tailscale` Check), holt das Binary
nur wenn nicht da, aktiviert tailscaled, setzt --operator. Auth-Key wird
hier nicht durchgereicht — Verbindung erfolgt nachträglich über die UI
(TailscaleCard → Connect).
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

INSTALL_TIMEOUT = 120.0  # apt + curl|sh kann auf langsamem Link dauern


async def install_tailscale() -> dict:
    """Ruft 80-tailscale.sh als root. Returnt rc + letzte Log-Zeilen.

    Wirft RuntimeError nicht — Fehler kommen als rc != 0 + stderr_tail
    zurück, damit das Frontend differenziert melden kann.
    """
    script = settings.base_dir / "installer" / "modules" / "80-tailscale.sh"
    if not script.exists():
        return {"ok": False, "rc": -1, "output": f"Skript nicht gefunden: {script}"}

    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", "bash", str(script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # gemeinsam, sortierte Reihenfolge
        env={"HH_INSTALL_TAILSCALE": "yes", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"},
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=INSTALL_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"ok": False, "rc": -1, "output": f"Timeout nach {INSTALL_TIMEOUT}s"}

    output = stdout.decode("utf-8", errors="replace")
    # Letzte ~30 Zeilen reichen für UI-Anzeige
    tail = "\n".join(output.splitlines()[-30:])
    rc = proc.returncode or 0
    if rc != 0:
        logger.warning("tailscale install rc=%s, tail=%r", rc, tail[-400:])
    return {"ok": rc == 0, "rc": rc, "output": tail}
