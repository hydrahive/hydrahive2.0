"""„Alle updaten“: alle Module mit verfügbarem Update ersetzen, EINMAL bauen, EINMAL neu starten.

docs/specs/modul-update-alle.md (Task b74c972d). Die frühere Schleife im Browser baute und startete je Modul neu;
der Neustart riss das nächste Update ab. Ein Fehler bei einem Modul stoppt die anderen nicht.
"""
from __future__ import annotations

import logging
import subprocess
from collections.abc import Iterator

from hydrahive.modules import installer
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_CAUGHT = (installer.InstallError, OSError, subprocess.CalledProcessError)


def _installed_versions() -> dict[str, str]:
    """Installierte Module (Ordner mit lesbarem Manifest) → Version. Kaputte oder versteckte Ordner fallen weg."""
    from hydrahive.modules.manifest import ManifestError, ModuleManifest
    out: dict[str, str] = {}
    if not settings.modules_dir.is_dir():
        return out
    for path in sorted(settings.modules_dir.iterdir()):
        if not path.is_dir() or path.name.startswith(".") or path.is_symlink():
            continue
        try:
            out[path.name] = ModuleManifest.load(path / "manifest.json").version
        except (ManifestError, OSError, ValueError):
            continue
    return out


def _reason(exc: BaseException) -> str:
    """Kurzer Grund in einfacher Sprache; der volle Fehler mit Pfad steht im Protokoll."""
    if isinstance(exc, installer.InstallError):
        return str(exc) or "Installationsfehler"
    if isinstance(exc, PermissionError):
        return "keine Schreibrechte auf den Modul-Ordner"
    if isinstance(exc, subprocess.CalledProcessError):
        return "Dienst des Moduls ließ sich nicht stoppen oder starten"
    return "Dateifehler beim Ersetzen"


def _version_of(module_id: str) -> str | None:
    return _installed_versions().get(module_id)


def _update_one(module_id: str) -> Iterator[str]:
    """Wie installer.update(), aber ohne Build und Neustart (die kommen am Ende einmal)."""
    yield from installer._ensure_dependencies(module_id, {module_id})
    # Stoppen nach dem ALTEN Manifest, Starten nach dem NEUEN – ein Update kann den ersten Dienst mitbringen
    # (Radiostream 0.2.0) oder ihn entfernen (docs/specs/modul-update-alle.md, Nachtrag 30.10.).
    if installer._manifest_has_service(module_id):
        installer._run_service_script(module_id, "uninstall.sh")
    installer.replace_module_in(module_id)
    if installer._manifest_has_service(module_id):
        installer._run_service_script(module_id, "install.sh")


def update_all() -> Iterator[str]:
    installer.refresh()
    installed = _installed_versions()
    todo = [(mid, ver) for mid, ver in installed.items()
            if installer.is_update_available(ver, installer.available_version(mid))]
    if not todo:
        yield "[modules] Alle Module sind aktuell"
        return

    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    for mid, old in todo:
        yield f"[modules] update {mid} …"
        try:
            yield from _update_one(mid)
        except _CAUGHT as exc:
            reason = _reason(exc)
            logger.exception("Modul-Update im Sammel-Update fehlgeschlagen: %s", mid)
            failed.append((mid, reason))
            yield f"[modules] {mid}: FEHLER – {reason}"
            continue
        ok.append(mid)
        yield f"[modules] {mid}: fertig ({old} → {_version_of(mid) or '?'})"

    if not ok:
        listed = ", ".join(f"{m} ({r})" for m, r in failed)
        raise installer.InstallError(f"module_update_all_failed: {listed}")

    yield "[modules] Frontend wird gebaut …"
    installer._frontend_build()
    yield "[modules] Frontend gebaut"
    installer._request_restart()
    yield "[modules] Neustart angefordert"
    yield f"[modules] Fertig: {len(ok)} aktualisiert, {len(failed)} fehlgeschlagen"
    if failed:
        yield "[modules] Fehlgeschlagen: " + ", ".join(f"{m} ({r})" for m, r in failed)
