"""Plugin-Discovery + Load.

Wird einmal beim Backend-Start aus `api/main.py::lifespan` aufgerufen.
Iteriert das `settings.plugins_dir`, parst jede `plugin.yaml`, importiert
das Entry-Modul, ruft `on_load(ctx)`. Fehler eines Plugins blockieren
nicht die anderen.
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path

from hydrahive.plugins.context import PluginContext
from hydrahive.plugins.manifest import ManifestError, PluginManifest
from hydrahive.plugins.registry import REGISTRY, LoadedPlugin
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def _discover(plugins_dir: Path) -> list[Path]:
    if not plugins_dir.exists():
        return []
    return sorted(
        p for p in plugins_dir.iterdir()
        if p.is_dir()
        and not p.name.startswith(".")
        and (p / "plugin.yaml").exists()
    )


def _module_name_for(plugin_dir: Path, manifest: PluginManifest) -> str:
    """Underscore-Form vom Plugin-Namen für Python-Import."""
    safe = manifest.name.replace("-", "_")
    if manifest.entry == "__init__":
        return safe
    return f"{safe}.{manifest.entry}"


def _import_plugin(plugin_dir: Path, manifest: PluginManifest):
    """Importiert das Entry-Modul.

    Trick: wir registrieren den underscore-Namen als Top-Level-Modul, damit
    Plugins mit `from <name>.tools.foo import …` arbeiten können.
    """
    safe = manifest.name.replace("-", "_")
    parent = str(plugin_dir.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(
        safe, plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"konnte Spec für {plugin_dir} nicht erzeugen")
    module = importlib.util.module_from_spec(spec)
    sys.modules[safe] = module
    spec.loader.exec_module(module)
    if manifest.entry == "__init__":
        return module
    return importlib.import_module(_module_name_for(plugin_dir, manifest))


def _load_one(plugin_dir: Path) -> LoadedPlugin:
    manifest_path = plugin_dir / "plugin.yaml"
    try:
        manifest = PluginManifest.from_file(manifest_path)
    except ManifestError as e:
        return LoadedPlugin(name=plugin_dir.name, manifest=None, error=str(e))

    try:
        module = _import_plugin(plugin_dir, manifest)
    except Exception as e:
        logger.exception("Plugin '%s' Import fehlgeschlagen", manifest.name)
        return LoadedPlugin(name=manifest.name, manifest=manifest, error=f"Import: {e}")

    on_load = getattr(module, "on_load", None)
    if not callable(on_load):
        return LoadedPlugin(
            name=manifest.name, manifest=manifest, module=module,
            error="entry-Modul hat keine on_load(ctx)-Funktion",
        )

    ctx = PluginContext(
        plugin_name=manifest.name,
        plugin_dir=plugin_dir,
        logger=logging.getLogger(f"plugins.{manifest.name}"),
    )
    try:
        on_load(ctx)
    except Exception as e:
        logger.exception("Plugin '%s' on_load fehlgeschlagen", manifest.name)
        return LoadedPlugin(
            name=manifest.name, manifest=manifest, module=module,
            error=f"on_load: {e}",
        )

    return LoadedPlugin(
        name=manifest.name, manifest=manifest, module=module, tools=ctx.tools,
    )


def load_all() -> None:
    """Idempotent: bei Wiederaufruf wird REGISTRY zurückgesetzt."""
    REGISTRY.clear()
    plugins_dir = settings.plugins_dir
    plugins_dir.mkdir(parents=True, exist_ok=True)
    found = _discover(plugins_dir)
    if not found:
        logger.info("Keine Plugins gefunden in %s", plugins_dir)
        return
    for plugin_dir in found:
        loaded = _load_one(plugin_dir)
        REGISTRY[loaded.name] = loaded
        if loaded.loaded:
            logger.info(
                "Plugin geladen: %s v%s (%d Tools)",
                loaded.name, loaded.manifest.version, len(loaded.tools),
            )
        else:
            logger.warning("Plugin '%s' nicht geladen: %s", loaded.name, loaded.error)
