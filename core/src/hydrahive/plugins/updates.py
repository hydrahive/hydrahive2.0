"""Neue Plugin-Versionen erkennen – wie bei den Modulen (docs/specs/plugin-updates.md).

Liest nur den VORHANDENEN Hub-Cache (``hub.json``) und die ``plugin.yaml`` auf der Platte – kein git, damit Liste und
Fußzeilen-Zähler billig bleiben. Aufgefrischt wird der Cache von ``GET /api/plugins/hub``. Fehler ergeben „kein
Update“ und werfen nie: Die Update-Erkennung darf die Plugin-Liste nicht sprengen.
"""
from __future__ import annotations

import json
import logging

from hydrahive.modules.installer import is_update_available
from hydrahive.plugins.manifest import ManifestError, PluginManifest
from hydrahive.plugins.registry import LoadedPlugin
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def hub_versions() -> dict[str, str]:
    """Name → Version laut ``hub.json`` im Cache; leer, wenn der Cache fehlt oder kaputt ist."""
    try:
        index = json.loads((settings.plugin_hub_cache / "hub.json").read_text(encoding="utf-8"))
        return {str(p["name"]): str(p["version"]) for p in index.get("plugins") or []
                if isinstance(p, dict) and p.get("name") and p.get("version")}
    except (OSError, ValueError, AttributeError) as exc:
        logger.debug("Plugin-Hub-Cache nicht lesbar: %s", exc)
        return {}


def disk_version(name: str) -> str | None:
    """Version der ``plugin.yaml`` auf der Platte (nach „Aktualisieren“ schon die neue, geladen noch die alte)."""
    try:
        return PluginManifest.from_file(settings.plugins_dir / name / "plugin.yaml").version
    except (OSError, ManifestError) as exc:
        logger.debug("plugin.yaml von %s nicht lesbar: %s", name, exc)
        return None


def status(plugin: LoadedPlugin, hub: dict[str, str]) -> dict:
    """Felder für die Liste: installed_version, available_version, update_available, restart_needed."""
    loaded = plugin.manifest.version if plugin.manifest else None
    on_disk = disk_version(plugin.name) or loaded
    available = hub.get(plugin.name)
    restart = bool(loaded and on_disk and on_disk != loaded)
    return {
        "installed_version": on_disk,
        "available_version": available,
        "update_available": is_update_available(on_disk, available),
        "restart_needed": restart,
    }


def update_count(plugins: list[LoadedPlugin]) -> int:
    hub = hub_versions()
    return sum(1 for p in plugins if status(p, hub)["update_available"])
