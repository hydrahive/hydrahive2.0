"""Modul-Installer: Dateioperationen (Task 8) + Orchestrierung (Task 11).

copy_module_in  — kopiert ein Modul aus dem Hub-Cache in:
  - settings.modules_dir/<id>   (backend + migrations + manifest + frontend-Kopie)
  - <base_dir>/frontend/src/modules/<id>  (frontend-Assets für den Vite-Build)

remove_module_files — entfernt beide Verzeichnisse.
  DB-Tabellen / Daten bleiben IMMER unangetastet.

install(module_id)   — Generator: kopieren → Dienst → Build → Restart
uninstall(module_id) — Generator: Dienst → entfernen → Build → Restart
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

from hydrahive.modules import hub_client
from hydrahive.modules.hub_client import refresh
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    """Wird geworfen wenn ein Modul nicht installiert werden kann."""


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")  # muss zu manifest._ID_RE passen


def _validate_module_id(module_id: str) -> None:
    if not _ID_RE.match(module_id):
        raise InstallError(f"ungültige module_id: {module_id!r}")


def _frontend_modules_dir() -> Path:
    """Ziel-Verzeichnis für Frontend-Assets im Repo (base_dir = /opt/hydrahive2)."""
    return settings.base_dir / "frontend" / "src" / "modules"


def _cache_path_for(module_id: str) -> Path:
    """Modul-Source im (passenden) Hub-Cache anhand des gemergten hub.json finden."""
    index = hub_client.read_hub_index()
    for entry in index.get("modules", []):
        if entry.get("id") == module_id:
            path = entry.get("path") or module_id
            return hub_client.module_source_path(path, entry.get("_hub"))
    raise InstallError(f"module_not_in_hub:{module_id}")


def available_version(module_id: str) -> str | None:
    """Version aus dem manifest.json des Moduls im Hub-Cache (ohne git-pull).

    Nutzt den bereits vorhandenen Hub-Cache — es wird NICHT frisch gepullt, damit
    der Aufruf billig bleibt (z.B. für den Footer-Zähler). Fehler/kein Manifest
    → None (nie werfen; Update-Erkennung darf die Modul-Liste nie sprengen).
    """
    from hydrahive.modules.manifest import ManifestError, ModuleManifest
    try:
        src = _cache_path_for(module_id)
        return ModuleManifest.load(src / "manifest.json").version
    except (InstallError, ManifestError, OSError) as exc:
        logger.debug("available_version(%s) nicht ermittelbar: %s", module_id, exc)
        return None


def available_description(module_id: str) -> str:
    """Beschreibung aus dem manifest.json des Moduls im Hub-Cache (ohne git-pull).

    Für die (noch) nicht installierte Ansicht — die installierte Beschreibung
    kommt aus dem REGISTRY-Manifest. Fehler/kein Manifest → "" (nie werfen).
    """
    from hydrahive.modules.manifest import ManifestError, ModuleManifest
    try:
        src = _cache_path_for(module_id)
        return ModuleManifest.load(src / "manifest.json").description
    except (InstallError, ManifestError, OSError) as exc:
        logger.debug("available_description(%s) nicht ermittelbar: %s", module_id, exc)
        return ""


def is_update_available(installed: str | None, available: str | None) -> bool:
    """True, wenn `available` eine neuere Version als `installed` ist.

    Semver-Vergleich via packaging.version; bei Parse-Fehler Fallback auf
    String-Ungleichheit (konservativ: unterschiedlich → Update anbieten).
    Fehlt eine der Versionen → kein Update.
    """
    if not installed or not available:
        return False
    from packaging.version import InvalidVersion, Version
    try:
        return Version(available) > Version(installed)
    except InvalidVersion:
        return available != installed


def copy_module_in(module_id: str) -> None:
    """Kopiert ein Modul aus dem Hub-Cache in die lokalen Verzeichnisse.

    symlinks=False ist bewusst: keine Symlinks als Escape-Vektor.
    """
    _validate_module_id(module_id)
    refresh()
    src = _cache_path_for(module_id)

    # Backend + migrations + manifest (+ frontend als passiver Sub-Dir) → modules_dir
    backend_dst = settings.modules_dir / module_id
    backend_dst.parent.mkdir(parents=True, exist_ok=True)
    if backend_dst.exists():
        shutil.rmtree(backend_dst)
    shutil.copytree(src, backend_dst, symlinks=False)
    logger.info("Modul '%s' Backend nach %s kopiert", module_id, backend_dst)

    # Frontend-Assets → <base_dir>/frontend/src/modules/<id> (optional)
    fe_src = src / "frontend"
    if fe_src.exists():
        fe_dst = _frontend_modules_dir() / module_id
        fe_dst.parent.mkdir(parents=True, exist_ok=True)
        if fe_dst.exists():
            shutil.rmtree(fe_dst)
        shutil.copytree(fe_src, fe_dst, symlinks=False)
        logger.info("Modul '%s' Frontend nach %s kopiert", module_id, fe_dst)


def remove_module_files(module_id: str) -> None:
    """Entfernt die Datei-Artefakte eines Moduls.

    DB-Tabellen, Daten und module_schema_version bleiben unangetastet —
    das ist die Datensicherheits-Garantie des Modulsystems.
    """
    _validate_module_id(module_id)
    for d in (
        settings.modules_dir / module_id,
        _frontend_modules_dir() / module_id,
    ):
        if d.exists():
            shutil.rmtree(d)
            logger.info("Modul-Verzeichnis entfernt: %s", d)


# ---------------------------------------------------------------------------
# Orchestrierung (Task 11)
# ---------------------------------------------------------------------------

def _frontend_build() -> None:
    fe = settings.base_dir / "frontend"
    subprocess.run(["npm", "run", "build"], cwd=fe, check=True)


def _request_restart() -> None:
    (settings.data_dir / ".restart_request").write_text("module-change")


def _manifest_has_service(module_id: str) -> bool:
    from hydrahive.modules.manifest import ModuleManifest
    return ModuleManifest.load(settings.modules_dir / module_id / "manifest.json").has_service


def _run_service_script(module_id: str, script: str) -> None:  # "install.sh" | "uninstall.sh"
    path = settings.modules_dir / module_id / "extension" / script
    if path.exists():
        subprocess.run(["bash", str(path)], check=True)


def install(module_id: str) -> Iterator[str]:
    _validate_module_id(module_id)
    yield f"[modules] installiere {module_id} …"
    copy_module_in(module_id); yield "[modules] Dateien kopiert"
    if _manifest_has_service(module_id):
        _run_service_script(module_id, "install.sh"); yield "[modules] Dienst installiert"
    _frontend_build(); yield "[modules] Frontend gebaut"
    _request_restart(); yield "[modules] Neustart angefordert — fertig"


def uninstall(module_id: str) -> Iterator[str]:
    _validate_module_id(module_id)
    yield f"[modules] deinstalliere {module_id} …"
    if _manifest_has_service(module_id):
        _run_service_script(module_id, "uninstall.sh"); yield "[modules] Dienst entfernt"
    remove_module_files(module_id); yield "[modules] Dateien entfernt (Daten bleiben)"
    _frontend_build(); yield "[modules] Frontend gebaut"
    _request_restart(); yield "[modules] Neustart angefordert — fertig"


def update(module_id: str) -> Iterator[str]:
    """Hub pullen + Dateien ersetzen + einmal bauen. Daten bleiben unangetastet."""
    _validate_module_id(module_id)
    yield f"[modules] update {module_id} …"
    if _manifest_has_service(module_id):
        _run_service_script(module_id, "uninstall.sh"); yield "[modules] Dienst gestoppt"
    remove_module_files(module_id); yield "[modules] alte Dateien entfernt"
    copy_module_in(module_id); yield "[modules] neue Dateien kopiert"
    if _manifest_has_service(module_id):
        _run_service_script(module_id, "install.sh"); yield "[modules] Dienst gestartet"
    _frontend_build(); yield "[modules] Frontend gebaut"
    _request_restart(); yield "[modules] Neustart angefordert — fertig"
