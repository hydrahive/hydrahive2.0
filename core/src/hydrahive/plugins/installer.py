"""Plugin-Install/Uninstall/Update gegen den Hub-Cache.

`install(name)` kopiert das Plugin aus dem Cache in das lokale Plugin-
Verzeichnis und ruft `load_all()` damit es sofort sichtbar wird.

`uninstall(name)` und `update(name)` setzen `restart_recommended=True` —
Module-Cache hält den alten Code, ein Service-Restart ist nötig damit
Code-Änderungen voll wirken.
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from hydrahive.plugins import hub_client, loader
from hydrahive.plugins.registry import REGISTRY
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    pass


@dataclass
class InstallResult:
    name: str
    version: str | None
    restart_recommended: bool = False


def _cache_path_for(name: str) -> Path:
    """Plugin-Source im Cache anhand hub.json finden."""
    index = hub_client.read_hub_index()
    for entry in index.get("plugins", []):
        if entry.get("name") == name:
            path = entry.get("path") or f"plugins/{name}"
            return hub_client.plugin_source_path(path)
    raise InstallError(f"plugin_not_in_hub:{name}")


def _local_path_for(name: str) -> Path:
    settings.plugins_dir.mkdir(parents=True, exist_ok=True)
    return settings.plugins_dir / name


def _remove_existing(dst: Path) -> None:
    """Räumt einen bestehenden Plugin-Pfad weg — egal ob Symlink oder Dir."""
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        shutil.rmtree(dst)


def install(name: str) -> InstallResult:
    src = _cache_path_for(name)
    if not src.exists():
        raise InstallError(f"plugin_source_missing:{name}")
    dst = _local_path_for(name)
    _remove_existing(dst)
    shutil.copytree(src, dst, symlinks=False)
    logger.info("Plugin '%s' installiert nach %s", name, dst)
    loader.load_all()
    plugin = REGISTRY.get(name)
    if plugin and plugin.error:
        # Aufgeräumt rein-installiert aber Loader-Fehler? Nicht löschen — User
        # soll den Fehler im UI sehen + manuell debuggen.
        raise InstallError(f"plugin_load_failed:{plugin.error}")
    return InstallResult(
        name=name,
        version=plugin.manifest.version if plugin and plugin.manifest else None,
    )


def uninstall(name: str) -> InstallResult:
    dst = _local_path_for(name)
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        shutil.rmtree(dst)
    REGISTRY.pop(name, None)
    logger.info("Plugin '%s' entfernt", name)
    return InstallResult(name=name, version=None, restart_recommended=True)


def update(name: str) -> InstallResult:
    hub_client.refresh()
    src = _cache_path_for(name)
    if not src.exists():
        raise InstallError(f"plugin_source_missing:{name}")
    dst = _local_path_for(name)
    _remove_existing(dst)
    shutil.copytree(src, dst, symlinks=False)
    logger.info("Plugin '%s' geupdated", name)
    return InstallResult(
        name=name,
        version=None,
        restart_recommended=True,
    )
