"""Gemeinsame Anfrage-Datei für installer/addon-ctl.sh (docs/specs/installer-core-first.md §3).

Genutzt von /api/system/addons und den alten Wegen (Voice, Samba, Tailscale), die eine Version lang weiter
funktionieren, aber denselben Runner anstoßen. Inhalt immer genau eine Zeile „install <modul>“ aus ADDONS.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import status

from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings
from hydrahive.system.addons_status import ADDONS

_REQUEST = re.compile(r"^install ([a-z]+)\s*$")


# Pfad erst beim Aufruf auflösen (settings.data_dir ist cached_property, siehe system_local_media.py).
def trigger_path() -> Path:
    return settings.data_dir / ".addon_request"


def running_addon(trigger: Path | None = None) -> str | None:
    """Name des laufenden Auftrags oder None. Fremde Inhalte gelten als „läuft“ („?“) – der Runner räumt sie weg."""
    trigger = trigger or trigger_path()
    try:
        text = trigger.read_text(errors="replace")[:64]
    except FileNotFoundError:
        return None
    except OSError:
        return "?"
    m = _REQUEST.match(text)
    return m.group(1) if m else "?"


def request_install(addon: str, trigger: Path | None = None) -> None:
    """Auftrag schreiben. 400 bei unbekanntem Modul, 409 wenn schon ein Auftrag läuft."""
    if addon not in ADDONS:
        raise coded(status.HTTP_400_BAD_REQUEST, "addon_unknown", addon=addon[:32])
    trigger = trigger or trigger_path()
    if running_addon(trigger) is not None:
        raise coded(status.HTTP_409_CONFLICT, "addon_busy")
    trigger.parent.mkdir(parents=True, exist_ok=True)
    trigger.write_text(f"install {addon}\n")
