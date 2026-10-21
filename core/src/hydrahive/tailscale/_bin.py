"""Wo liegt die Tailscale-Kommandozeile? (Plan docs/plans/mac-agentlink.md)

Linux: im PATH bzw. /usr/bin/tailscale. macOS: die Tailscale-App bringt ihre CLI im App-Bündel mit,
nicht im PATH des HydraHive-Dienstes (launchd setzt einen festen PATH). Ohne diesen Weg gilt Tailscale
auf dem Mac als „nicht installiert“, und die Server-Kopplung lässt sich nicht einrichten.
"""
from __future__ import annotations

import os
import shutil

MACOS_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
LINUX_DEFAULT = "/usr/bin/tailscale"


def find_tailscale() -> str | None:
    """Pfad zur Tailscale-CLI oder None, wenn keine gefunden wird."""
    found = shutil.which("tailscale")
    if found:
        return found
    if os.path.isfile(MACOS_APP_CLI) and os.access(MACOS_APP_CLI, os.X_OK):
        return MACOS_APP_CLI
    return None


def tailscale_bin() -> str:
    """Pfad zum Aufrufen; ohne Fund der Linux-Standardpfad (der Aufruf meldet dann den Fehler)."""
    return find_tailscale() or LINUX_DEFAULT
