"""Registry installierter Themes — Scan des Frontend-Theme-Ordners.

Anders als das Modulsystem (das Python-Backend lädt) sind Themes reines
Frontend. „Installiert" heißt: Ordner mit theme.json existiert unter
settings.themes_frontend_dir. Die eingebauten Themes (standard/sidebar) sowie
das mitgelieferte aurora sind geschützt und nicht deinstallierbar.
"""
from __future__ import annotations

import logging

from hydrahive.settings import settings
from hydrahive.themes.manifest import ManifestError, ThemeManifest

logger = logging.getLogger(__name__)

# Nicht deinstallierbar: eingebaute Layout-Themes (im Frontend-Code) + das
# mitgelieferte Beispiel-Theme (lebende Vorlage, im Repo getrackt).
PROTECTED_THEME_IDS = frozenset({"standard", "sidebar", "aurora"})


def list_installed() -> list[dict]:
    """Alle installierten Theme-Pakete (Ordner mit theme.json) als dicts.

    Eingebaute Themes (standard/sidebar) leben im Frontend-Code ohne eigenes
    Paket-Verzeichnis und tauchen hier nicht auf — sie sind immer verfügbar.
    """
    root = settings.themes_frontend_dir
    if not root.exists():
        return []
    out: list[dict] = []
    for entry in sorted(root.iterdir()):
        manifest_path = entry / "theme.json"
        if not entry.is_dir() or not manifest_path.exists():
            continue
        try:
            m = ThemeManifest.load(manifest_path)
        except ManifestError as e:
            out.append({"id": entry.name, "loaded": False, "error": str(e), "version": None})
            continue
        out.append({
            "id": m.id,
            "name": m.name,
            "loaded": True,
            "error": None,
            "version": m.version,
            "protected": m.id in PROTECTED_THEME_IDS,
        })
    return out


def is_protected(theme_id: str) -> bool:
    return theme_id in PROTECTED_THEME_IDS
