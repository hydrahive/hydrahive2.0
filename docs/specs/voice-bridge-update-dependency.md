# Voice-Bridge-Abhängigkeit updatefest installieren

## Problem

Die lokale HA-Voice-PE-Bridge läuft mit dem HydraHive-Core-Interpreter und importiert
`aioesphomeapi`. Bislang war dieses Paket nur manuell in der Core-venv installiert.
Wird die venv bei einem Distributions-/Python-Upgrade neu aufgebaut, verschwindet das
Paket und `hydra-voice-bridge.service` gerät mit `ModuleNotFoundError` in eine
Restart-Schleife.

## Bestehendes Update-Pattern

Sowohl die Erstinstallation (`installer/modules/30-python.sh`) als auch jedes reguläre
Update (`installer/update.sh`) installieren `hydrahive-core` inklusive der in
`core/pyproject.toml` deklarierten Runtime-Abhängigkeiten. Der Ubuntu-26.04-Pfad baut
eine inkompatible venv vor dieser Installation kontrolliert neu auf.

## Optionen

### A. Runtime-Abhängigkeit im Core deklarieren (Hotfix)

- Vorteil: greift automatisch bei Erstinstallation, normalem Update und venv-Rebuild.
- Vorteil: kleinster Eingriff für den heutigen Rollout; Python 3.12 und 3.14 werden vom
  Paket unterstützt.
- Nachteil: Jede HydraHive-Installation erhält das Paket, auch ohne Voice-Hardware.

### B. Voice-Bridge als Modul-Service paketieren

- Vorteil: Abhängigkeit wird nur mit dem Voice-Modul installiert.
- Nachteil: Die Bridge liegt derzeit außerhalb des Modul-Repositories; Service-,
  Secret-, Geräte- und Uninstall-Lifecycle müssten vor einem Release neu entworfen
  und migriert werden.

### C. Separates `hh-voice-bridge`-Paket mit eigener venv

- Vorteil: langfristig sauberste Isolation.
- Nachteil: eigener Release-, Update-, Migrations- und systemd-Lifecycle; für den
  kurzfristigen Rollout unnötig riskant.

## Entscheidung

Für den kurzfristigen, rückwärtskompatiblen Hotfix wird Option A umgesetzt:
`aioesphomeapi>=45.3.1,<46` wird direkte Core-Runtime-Abhängigkeit. Die Untergrenze ist
die auf Python 3.14 und mit der bestehenden Bridge live verifizierte Version; die
Major-Obergrenze folgt der Dependency-Pinning-Policy.

Ein separates Bridge-Paket bleibt die langfristige Zielarchitektur und ist nicht Teil
dieses Hotfixes.

## Akzeptanzkriterien

- `aioesphomeapi` ist eine direkte, begrenzte Core-Runtime-Abhängigkeit.
- Der Installer- und Update-Pfad installieren weiterhin `hydrahive-core` inklusive
  Dependencies nach einem möglichen venv-Rebuild.
- Eine frische isolierte Python-3.12/3.14-Installation kann `aioesphomeapi`,
  `APIClient` und `MediaPlayerCommand` importieren.
- Der aufgerüstete Produktivdienst bleibt verbunden und restartfrei.
- Bestehende Core-Tests, Ruff und Dependency-Integritätsprüfung bleiben grün.
