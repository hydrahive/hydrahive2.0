"""Modul-Installer: Dateioperationen (Task 8).

copy_module_in  — kopiert ein Modul aus dem Hub-Cache in:
  - settings.modules_dir/<id>   (backend + migrations + manifest + frontend-Kopie)
  - <base_dir>/frontend/src/modules/<id>  (frontend-Assets für den Vite-Build)

remove_module_files — entfernt beide Verzeichnisse.
  DB-Tabellen / Daten bleiben IMMER unangetastet.

Orchestrierung (build, restart, service-Generator) ist Task 11 — nicht hier.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from hydrahive.modules import hub_client
from hydrahive.modules.hub_client import refresh
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    """Wird geworfen wenn ein Modul nicht installiert werden kann."""


def _frontend_modules_dir() -> Path:
    """Ziel-Verzeichnis für Frontend-Assets im Repo (base_dir = /opt/hydrahive2)."""
    return settings.base_dir / "frontend" / "src" / "modules"


def _cache_path_for(module_id: str) -> Path:
    """Modul-Source im Hub-Cache anhand hub.json finden."""
    index = hub_client.read_hub_index()
    for entry in index.get("modules", []):
        if entry.get("id") == module_id:
            path = entry.get("path") or module_id
            return hub_client.module_source_path(path)
    raise InstallError(f"module_not_in_hub:{module_id}")


def copy_module_in(module_id: str) -> None:
    """Kopiert ein Modul aus dem Hub-Cache in die lokalen Verzeichnisse.

    symlinks=False ist bewusst: keine Symlinks als Escape-Vektor.
    """
    refresh()
    src = _cache_path_for(module_id)

    # Backend + migrations + manifest (+ frontend als passiver Sub-Dir) → modules_dir
    backend_dst = settings.modules_dir / module_id
    backend_dst.parent.mkdir(parents=True, exist_ok=True)
    if backend_dst.exists():
        shutil.rmtree(backend_dst)
    shutil.copytree(src, backend_dst, symlinks=False)
    logger.info("Modul '%s' Backend nach %s kopiert", module_id, backend_dst)

    # Frontend-Assets → <base_dir>/frontend/src/modules/<id>
    fe_dst = _frontend_modules_dir() / module_id
    fe_dst.parent.mkdir(parents=True, exist_ok=True)
    if fe_dst.exists():
        shutil.rmtree(fe_dst)
    shutil.copytree(src / "frontend", fe_dst, symlinks=False)
    logger.info("Modul '%s' Frontend nach %s kopiert", module_id, fe_dst)


def remove_module_files(module_id: str) -> None:
    """Entfernt die Datei-Artefakte eines Moduls.

    DB-Tabellen, Daten und module_schema_version bleiben unangetastet —
    das ist die Datensicherheits-Garantie des Modulsystems.
    """
    for d in (
        settings.modules_dir / module_id,
        _frontend_modules_dir() / module_id,
    ):
        if d.exists():
            shutil.rmtree(d)
            logger.info("Modul-Verzeichnis entfernt: %s", d)
