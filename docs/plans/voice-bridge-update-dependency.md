# Plan: Voice-Bridge-Abhängigkeit updatefest installieren

## Ziel

Jeder reguläre HydraHive-Installations- und Update-Lauf installiert die für die
bestehende Voice-Bridge erforderliche ESPHome-API-Bibliothek automatisch, auch wenn
die Core-venv neu aufgebaut wurde.

## Dateien

- `core/pyproject.toml` — direkte, begrenzte Runtime-Abhängigkeit deklarieren.
- `core/tests/test_python_venv_installer.py` — Regressionsschutz für Dependency und
  bestehende Install-/Update-Pfade.
- `docs/specs/voice-bridge-update-dependency.md` — Entscheidung und Scope.

## Implementierungsreihenfolge

### Task 1: Automatische Runtime-Installation absichern

- [ ] Test ergänzen, der die direkte `aioesphomeapi`-Dependency mit Unter- und
  Obergrenze fordert.
- [ ] Test ausführen und RED wegen fehlender Dependency bestätigen.
- [ ] `aioesphomeapi>=45.3.1,<46` in `core/pyproject.toml` ergänzen.
- [ ] Fokussierte Tests und Ruff ausführen (GREEN).
- [ ] In einer frischen temporären venv das Core-Paket installieren und Bridge-Imports
  sowie `pip check` verifizieren.
- [ ] Produktiven Updatepfad/Bridge-Health prüfen.
- [ ] Commit und PR erstellen.

## Akzeptanzkriterien

- [ ] Erstinstallation und Update installieren die Dependency aus Core-Metadaten.
- [ ] Frische venv kann die von der Bridge benötigten ESPHome-Symbole importieren.
- [ ] Keine kaputten Python-Abhängigkeiten.
- [ ] Produktive Bridge bleibt `connected: true` mit `NRestarts=0`.

## Nicht in diesem Plan

- Verteilung des derzeit lokalen `voice-pe/bridge`-Quellcodes.
- Multi-Device-Registry, Pairing, Firmware-/Secret-Lifecycle.
- Migration auf eine eigene Voice-Bridge-venv; dies folgt separat.
