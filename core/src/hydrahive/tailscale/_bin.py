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


def _executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)


def find_tailscale() -> str | None:
    """Pfad zur Tailscale-CLI oder None, wenn keine gefunden wird.

    Ist die Tailscale-App installiert, gilt immer sie – auch wenn der eigene Build noch im PATH des Dienstes steht.
    Beide vertragen sich nicht; 80-tailscale.sh schaltet den eigenen Dienst dann ab (Befund Berkan 26.10.2026:
    gefragt wurde die tote eigene CLI, obwohl die App lief → „Mit Browser anmelden“ scheiterte).
    """
    if _executable(MACOS_APP_CLI):
        return MACOS_APP_CLI
    found = shutil.which("tailscale")
    if found:
        return found
    if _executable(MAC_OWN_CLI):
        return MAC_OWN_CLI
    return None


def tailscale_bin() -> str:
    """Pfad zum Aufrufen; ohne Fund der Linux-Standardpfad (der Aufruf meldet dann den Fehler)."""
    return find_tailscale() or LINUX_DEFAULT
