"""Wo liegt die Tailscale-Kommandozeile? (Plan docs/plans/mac-agentlink.md)

Linux: im PATH bzw. /usr/bin/tailscale. macOS: entweder HydraHives eigener Build (installer/modules-mac/
80-tailscale.sh, docs/plans/mac-tailscale.md) oder die CLI im Bündel der Tailscale-App – beide liegen nicht im festen
PATH des HydraHive-Dienstes (launchd). Ohne diese Wege gilt Tailscale auf dem Mac als „nicht installiert“.
"""
from __future__ import annotations

import os
import shutil

MAC_OWN_CLI = "/usr/local/lib/hydrahive2/tailscale/bin/tailscale"
MACOS_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
LINUX_DEFAULT = "/usr/bin/tailscale"


def find_tailscale() -> str | None:
    """Pfad zur Tailscale-CLI oder None, wenn keine gefunden wird."""
    found = shutil.which("tailscale")
    if found:
        return found
    for candidate in (MAC_OWN_CLI, MACOS_APP_CLI):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def tailscale_bin() -> str:
    """Pfad zum Aufrufen; ohne Fund der Linux-Standardpfad (der Aufruf meldet dann den Fehler)."""
    return find_tailscale() or LINUX_DEFAULT
