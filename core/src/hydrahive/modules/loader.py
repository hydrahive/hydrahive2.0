"""Modul-Discovery + Load.

Wird einmal beim Backend-Start aufgerufen.  Iteriert `settings.modules_dir`,
liest `manifest.json`, importiert `backend/__init__.py`, ruft `register(ctx)`,
wendet Migrationen an.  Fehler eines Moduls blockieren die anderen nicht.
"""
from __future__ import annotations

import importlib.util
import logging
import shutil
import sys
import types
from pathlib import Path

from hydrahive.modules.manifest import ManifestError, ModuleManifest
from hydrahive.modules.context import ModuleContext
from hydrahive.modules.registry import REGISTRY, LoadedModule
from hydrahive.modules.migrations import apply_module_migrations

logger = logging.getLogger(__name__)

# Module, die von Core-UI/Features direkt erwartet werden. Sie bleiben normale
# Runtime-Module unter settings.modules_dir, werden aber aus dem gebündelten Repo-
# Verzeichnis repariert, falls eine Installation fehlt oder offensichtlich kaputt
# ist (z.B. leeres /var/lib/hydrahive2/modules/tasks ohne manifest.json).
REQUIRED_BUNDLED_MODULES = ("tasks",)


def ensure_required_bundled_modules() -> None:
    """Stellt sicher, dass Core-erwartete gebündelte Module installierbar sind.

    Normale installierte Module werden nicht überschrieben. Repariert wird nur,
    wenn das Ziel fehlt oder kein manifest.json enthält. Damit werden User-Daten
    in Modul-DB-Tabellen nicht angefasst und bewusst installierte Modulstände
    bleiben erhalten, während ein kaputtes/leeres Modulverzeichnis keinen 404 für
    Core-Cockpit-Funktionen verursacht.
    """
    from hydrahive.settings import settings  # lazy: Settings-Pfade erst zur Laufzeit binden

    bundled_base = settings.base_dir / "modules"
    settings.modules_dir.mkdir(parents=True, exist_ok=True)
    for module_id in REQUIRED_BUNDLED_MODULES:
        src = bundled_base / module_id
        dst = settings.modules_dir / module_id
        if not (src / "manifest.json").is_file():
            logger.warning("Gebündeltes Pflichtmodul '%s' fehlt unter %s", module_id, src)
            continue
        if (dst / "manifest.json").is_file():
            continue
        if dst.exists():
            shutil.rmtree(dst)
            logger.warning("Kaputtes Pflichtmodul '%s' ohne manifest.json entfernt: %s", module_id, dst)
        shutil.copytree(src, dst, symlinks=False)
        logger.info("Pflichtmodul '%s' aus Bundle installiert: %s", module_id, dst)


def _import_backend(module_dir: Path, mid: str) -> types.ModuleType:
    """Importiert backend/__init__.py mit dem Plugin-Loader-Idiom.

    Folgt demselben Idiom wie plugins/loader.py (spec_from_file_location +
    sys.path-Eintrag + sys.modules-Registrierung), damit relative Imports im
    Modul-Backend funktionieren.  Hinweis: der sys.path-Eintrag und der
    sys.modules-Eintrag bleiben für die gesamte Prozess-Laufzeit erhalten;
    das Bereinigen von entfernten Modulen obliegt dem Backend-Neustart
    (by design).
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

    if name.replace("-", "_") != manifest.id.replace("-", "_"):
        logger.warning("Modul-Verzeichnis %r weicht von manifest.id %r ab", name, manifest.id)

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
    for module_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")):
        loaded = _load_one(module_dir)
        REGISTRY[loaded.name] = loaded
        if loaded.loaded:
            logger.info(
                "Modul '%s' geladen (v%s)", loaded.name, loaded.manifest.version
            )
        else:
            logger.warning("Modul '%s' nicht geladen: %s", loaded.name, loaded.error)
