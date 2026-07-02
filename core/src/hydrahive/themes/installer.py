"""Theme-Installer: Dateioperationen + Orchestrierung.

Schlanker als der Modul-Installer, weil ein Theme reines Frontend ist:
EIN Kopierziel (settings.themes_frontend_dir/<id>), kein Service, keine DB.

copy_theme_in(id)     — kopiert ein Theme aus dem Hub-Cache ins Frontend-Paket.
remove_theme_files(id)— entfernt den Ordner (geschützte Themes nie).
install(id)           — Generator: kopieren → Build → Restart-Request.
uninstall(id)         — Generator: entfernen → Build → Restart-Request.
update(id)            — Generator: entfernen → kopieren → Build → Restart.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.themes import hub_client
from hydrahive.themes.hub_client import refresh
from hydrahive.themes.registry import is_protected

logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    """Wird geworfen wenn ein Theme nicht installiert werden kann."""


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")  # muss zu manifest._ID_RE passen


def _validate_theme_id(theme_id: str) -> None:
    if not _ID_RE.match(theme_id):
        raise InstallError(f"ungültige theme_id: {theme_id!r}")


def _cache_path_for(theme_id: str) -> Path:
    """Theme-Source im (passenden) Hub-Cache anhand des gemergten hub.json finden."""
    index = hub_client.read_hub_index()
    for entry in index.get("themes", []):
        if entry.get("id") == theme_id:
            path = entry.get("path") or theme_id
            return hub_client.theme_source_path(path, entry.get("_hub"))
    raise InstallError(f"theme_not_in_hub:{theme_id}")


def copy_theme_in(theme_id: str) -> None:
    """Kopiert ein Theme aus dem Hub-Cache in den Frontend-Paket-Ordner.

    symlinks=False ist bewusst: keine Symlinks als Escape-Vektor.
    """
    _validate_theme_id(theme_id)
    refresh()
    src = _cache_path_for(theme_id)

    dst = settings.themes_frontend_dir / theme_id
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=False)
    logger.info("Theme '%s' nach %s kopiert", theme_id, dst)


def remove_theme_files(theme_id: str) -> None:
    """Entfernt das Theme-Paket-Verzeichnis. Geschützte Themes sind tabu."""
    _validate_theme_id(theme_id)
    if is_protected(theme_id):
        raise InstallError(f"theme_protected:{theme_id}")
    d = settings.themes_frontend_dir / theme_id
    if d.exists():
        shutil.rmtree(d)
        logger.info("Theme-Verzeichnis entfernt: %s", d)


# ---------------------------------------------------------------------------
# Orchestrierung
# ---------------------------------------------------------------------------

def _frontend_build() -> None:
    fe = settings.base_dir / "frontend"
    subprocess.run(["npm", "run", "build"], cwd=fe, check=True)


def _request_restart() -> None:
    (settings.data_dir / ".restart_request").write_text("theme-change")


def install(theme_id: str) -> Iterator[str]:
    _validate_theme_id(theme_id)
    yield f"[themes] installiere {theme_id} …"
    copy_theme_in(theme_id); yield "[themes] Dateien kopiert"
    _frontend_build(); yield "[themes] Frontend gebaut"
    _request_restart(); yield "[themes] Neustart angefordert — fertig"


def uninstall(theme_id: str) -> Iterator[str]:
    _validate_theme_id(theme_id)
    if is_protected(theme_id):
        raise InstallError(f"theme_protected:{theme_id}")
    yield f"[themes] deinstalliere {theme_id} …"
    remove_theme_files(theme_id); yield "[themes] Dateien entfernt"
    _frontend_build(); yield "[themes] Frontend gebaut"
    _request_restart(); yield "[themes] Neustart angefordert — fertig"


def update(theme_id: str) -> Iterator[str]:
    """Hub pullen + Dateien ersetzen + einmal bauen."""
    _validate_theme_id(theme_id)
    yield f"[themes] update {theme_id} …"
    copy_theme_in(theme_id); yield "[themes] neue Dateien kopiert"
    _frontend_build(); yield "[themes] Frontend gebaut"
    _request_restart(); yield "[themes] Neustart angefordert — fertig"


def publish(theme_id: str) -> Iterator[str]:
    """Editierte Theme-Dateien ins laufende Frontend übernehmen (Build + Restart).

    Anders als update() wird NICHT aus dem Hub kopiert — die Quelle ist der
    bereits im Frontend-Ordner liegende (im Editor bearbeitete) Theme-Ordner.
    Der Build bettet die geänderten Templates via gen-themes.mjs neu ein.
    """
    _validate_theme_id(theme_id)
    if not (settings.themes_frontend_dir / theme_id).is_dir():
        raise InstallError(f"theme_not_found:{theme_id}")
    yield f"[themes] veröffentliche {theme_id} …"
    _frontend_build(); yield "[themes] Frontend gebaut"
    _request_restart(); yield "[themes] Neustart angefordert — fertig"
