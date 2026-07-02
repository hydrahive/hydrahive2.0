"""Theme-Editor-Persistenz: Template-HTML lesen/schreiben + Theme forken.

Etappe 2 des Theme-Editors. Ein Theme-Paket liegt als echter Ordner unter
settings.themes_frontend_dir/<id>/ mit templates/<route>.html. Dieses Modul
erlaubt es, diese Template-Dateien über die API zu lesen und (für nicht
geschützte User-Themes) zu schreiben — die Datenbasis für den WYSIWYG-Editor.

Sicherheit (Datei-Schreiben über API!):
- theme_id + route streng validiert (Whitelist-Regex, kein '/', kein '..').
- Zielpfad wird via resolve() geprüft: muss echt INNERHALB des Theme-Ordners
  liegen (Schutz gegen Pfad-Traversal / Symlink-Escape).
- Geschützte Themes (standard/sidebar/aurora) sind read-only — man forkt sie
  in ein eigenes User-Theme und editiert die Kopie.

Kein Build hier: das Schreiben ändert nur die Quelldatei. Das Übernehmen ins
laufende Frontend (Build) ist ein separater, expliziter "Publish"-Schritt
(installer._frontend_build), damit nicht jeder Tastendruck baut.
"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.themes.manifest import ManifestError, ThemeManifest
from hydrahive.themes.registry import is_protected

logger = logging.getLogger(__name__)

# Muss zu manifest._ID_RE passen (a-z0-9-, Start alphanumerisch).
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Routen sind einfache Bezeichner (Dateiname ohne .html), z.B. "buddy".
_ROUTE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Obergrenze pro Template, damit die API nicht als Datei-Dump missbraucht wird.
_MAX_TEMPLATE_BYTES = 256 * 1024


class EditorError(RuntimeError):
    """Wird geworfen bei ungültigen Eingaben oder verbotenen Operationen."""


def _validate_id(theme_id: str) -> None:
    if not _ID_RE.match(theme_id or ""):
        raise EditorError(f"ungültige theme_id: {theme_id!r}")


def _validate_route(route: str) -> None:
    if not _ROUTE_RE.match(route or ""):
        raise EditorError(f"ungültige route: {route!r}")


def _theme_dir(theme_id: str) -> Path:
    """Verzeichnis eines Theme-Pakets, garantiert innerhalb themes_frontend_dir."""
    _validate_id(theme_id)
    root = settings.themes_frontend_dir.resolve()
    d = (root / theme_id).resolve()
    # Pfad-Traversal-Schutz: d muss ein direktes Kind von root sein.
    if d.parent != root:
        raise EditorError(f"theme-pfad ausserhalb der theme-wurzel: {theme_id!r}")
    return d


def _template_path(theme_id: str, route: str) -> Path:
    """Pfad zu templates/<route>.html, sicher innerhalb des Theme-Ordners."""
    _validate_route(route)
    tdir = _theme_dir(theme_id)
    tpl_root = (tdir / "templates").resolve()
    p = (tpl_root / f"{route}.html").resolve()
    if p.parent != tpl_root:
        raise EditorError(f"template-pfad ausserhalb templates/: {route!r}")
    return p


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------

def list_templates(theme_id: str) -> list[str]:
    """Alle Routen (Template-Dateinamen ohne .html) eines Themes, sortiert."""
    tdir = _theme_dir(theme_id)
    tpl_root = tdir / "templates"
    if not tpl_root.is_dir():
        return []
    return sorted(
        p.stem for p in tpl_root.iterdir()
        if p.is_file() and p.suffix == ".html"
    )


def read_template(theme_id: str, route: str) -> str:
    """Rohes Template-HTML lesen. Fehlt die Datei → leerer String."""
    p = _template_path(theme_id, route)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Schreiben (nur nicht-geschützte Themes)
# ---------------------------------------------------------------------------

def _assert_editable(theme_id: str) -> None:
    if is_protected(theme_id):
        raise EditorError(f"theme_protected:{theme_id}")
    if not _theme_dir(theme_id).is_dir():
        raise EditorError(f"theme_not_found:{theme_id}")


def write_template(theme_id: str, route: str, html: str) -> None:
    """Template-HTML schreiben. Nur für nicht-geschützte User-Themes.

    Das Verzeichnis templates/ wird bei Bedarf angelegt. Kein Build — die
    Änderung ist erst nach einem Publish (Build) im laufenden Frontend sichtbar.
    """
    _assert_editable(theme_id)
    if len(html.encode("utf-8")) > _MAX_TEMPLATE_BYTES:
        raise EditorError("template_too_large")
    p = _template_path(theme_id, route)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    logger.info("Template '%s/%s' geschrieben (%d B)", theme_id, route, len(html))


def delete_template(theme_id: str, route: str) -> None:
    """Ein Template löschen (Route fällt auf den React-Fallback zurück)."""
    _assert_editable(theme_id)
    p = _template_path(theme_id, route)
    if p.is_file():
        p.unlink()
        logger.info("Template '%s/%s' gelöscht", theme_id, route)


# ---------------------------------------------------------------------------
# Fork: geschütztes/Vorlagen-Theme → editierbares User-Theme kopieren
# ---------------------------------------------------------------------------

def fork_theme(source_id: str, new_id: str, new_name: str) -> dict:
    """Kopiert ein bestehendes Theme in ein neues, editierbares User-Theme.

    So bleibt die Vorlage (z.B. das geschützte 'aurora') unangetastet und man
    gestaltet die Kopie. new_id muss frei sein und darf nicht geschützt sein.
    """
    _validate_id(source_id)
    _validate_id(new_id)
    if is_protected(new_id):
        raise EditorError(f"ziel_id_geschuetzt:{new_id}")
    src = _theme_dir(source_id)
    if not src.is_dir():
        raise EditorError(f"quelle_nicht_gefunden:{source_id}")
    dst = _theme_dir(new_id)
    if dst.exists():
        raise EditorError(f"ziel_existiert:{new_id}")

    shutil.copytree(src, dst, symlinks=False)

    # Manifest der Kopie auf neue id/name umschreiben (+ als user-fork markieren).
    manifest_path = dst / "theme.json"
    try:
        m = ThemeManifest.load(manifest_path)
    except ManifestError as e:
        shutil.rmtree(dst, ignore_errors=True)
        raise EditorError(f"quell_manifest_ungueltig:{e}") from e

    import json
    data = {
        "id": new_id,
        "name": new_name or new_id,
        "version": "1.0.0",
        "description": f"Fork von {m.name}",
        "author": "user",
        "layout": m.layout,
        "variables": dict(m.variables),
        "min_core_version": m.min_core_version,
    }
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Theme '%s' nach '%s' geforkt", source_id, new_id)
    return {"id": new_id, "name": data["name"], "source": source_id}
