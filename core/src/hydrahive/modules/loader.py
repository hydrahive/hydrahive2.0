"""Modul-Discovery + Load.

Wird einmal beim Backend-Start aufgerufen.  Iteriert `settings.modules_dir`,
liest `manifest.json`, importiert `backend/__init__.py`, ruft `register(ctx)`,
wendet Migrationen an.  Fehler eines Moduls blockieren die anderen nicht.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from hydrahive.modules.manifest import ManifestError, ModuleManifest
from hydrahive.modules.context import ModuleContext
from hydrahive.modules.registry import REGISTRY, LoadedModule
from hydrahive.modules.migrations import apply_module_migrations

logger = logging.getLogger(__name__)


def _import_backend(module_dir: Path, mid: str):
    """Importiert backend/__init__.py mit dem Plugin-Loader-Idiom.

    Analog zu plugins/loader.py:43-66 — spec_from_file_location +
    sys.path + sys.modules — damit relative Imports im Modul funktionieren.
    """
    safe = "hhmod_" + mid.replace("-", "_")
    backend = module_dir / "backend"
    parent = str(backend.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(
        safe, backend / "__init__.py",
        submodule_search_locations=[str(backend)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Spec für {backend} nicht erzeugbar")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[safe] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_one(module_dir: Path) -> LoadedModule:
    name = module_dir.name
    try:
        manifest = ModuleManifest.load(module_dir / "manifest.json")
    except ManifestError as e:
        return LoadedModule(name=name, manifest=None, path=module_dir, error=str(e))

    try:
        backend = _import_backend(module_dir, manifest.id)
        register = getattr(backend, "register", None)
        if not callable(register):
            return LoadedModule(
                name=name, manifest=manifest, path=module_dir,
                error="backend/__init__.py hat kein register(ctx)",
            )
        ctx = ModuleContext(manifest.id)
        register(ctx)
        if ctx.migrations_rel:
            apply_module_migrations(manifest.id, module_dir / ctx.migrations_rel)
    except Exception as e:
        logger.exception("Modul '%s' Laden fehlgeschlagen", name)
        return LoadedModule(name=name, manifest=manifest, path=module_dir, error=str(e))

    return LoadedModule(
        name=name, manifest=manifest, path=module_dir, ctx=ctx, loaded=True,
    )


def load_all() -> None:
    """Idempotent: bei Wiederaufruf wird REGISTRY zurückgesetzt."""
    from hydrahive.settings import settings  # lazy: data_dir-Freeze vermeiden

    REGISTRY.clear()
    base = settings.modules_dir
    if not base.is_dir():
        return
    for module_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        loaded = _load_one(module_dir)
        REGISTRY[loaded.name] = loaded
        if loaded.loaded:
            logger.info(
                "Modul '%s' geladen (v%s)", loaded.name, loaded.manifest.version
            )
        else:
            logger.warning("Modul '%s' nicht geladen: %s", loaded.name, loaded.error)
