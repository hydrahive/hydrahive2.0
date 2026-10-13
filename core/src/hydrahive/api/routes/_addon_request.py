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
# Feste Zusatz-Aktion (Archiv Etappe 1b): Platte für das Archiv einrichten. Nur eine 12-stellige ID aus der
# Platten-Liste – der Runner sucht sie in seiner eigenen Liste (installer/lib/archive-disk.sh), nie ein Pfad.
_PREPARE = re.compile(r"^prepare-archive ([0-9a-f]{12})\s*$")


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
    if m:
        return m.group(1)
    return "prepare-archive" if _PREPARE.match(text) else "?"


def request_install(addon: str, trigger: Path | None = None) -> None:
    """Auftrag schreiben. 400 bei unbekanntem Modul, 409 wenn schon ein Auftrag läuft."""
    if addon not in ADDONS:
        raise coded(status.HTTP_400_BAD_REQUEST, "addon_unknown", addon=addon[:32])
    trigger = trigger or trigger_path()
    if running_addon(trigger) is not None:
        raise coded(status.HTTP_409_CONFLICT, "addon_busy")
    trigger.parent.mkdir(parents=True, exist_ok=True)
    trigger.write_text(f"install {addon}\n")


def request_prepare_archive(disk_id: str, trigger: Path | None = None) -> None:
    """Root-Runner soll <platte>/hydrahive-archiv für den Dienst anlegen. 400 bei falscher ID, 409 wenn belegt."""
    if not re.fullmatch(r"[0-9a-f]{12}", disk_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "archive_location_unknown")
    trigger = trigger or trigger_path()
    if running_addon(trigger) is not None:
        raise coded(status.HTTP_409_CONFLICT, "addon_busy")
    trigger.parent.mkdir(parents=True, exist_ok=True)
    trigger.write_text(f"prepare-archive {disk_id}\n")
