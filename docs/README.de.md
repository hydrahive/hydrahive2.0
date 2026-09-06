# HydraHive-Dokumentation

> 🇬🇧 [English version](README.md)

Dieses Verzeichnis enthält Produkt-, Operator-, Architektur-, Sicherheits- und Implementierungs-Dokumentation für HydraHive.

> **Hier starten:** [FEATURES.md](FEATURES.md) bzw. [FEATURES.de.md](FEATURES.de.md) ist das code-gestützte Inventar des aktuellen Produkts. `SPEC.md` bleibt die bindende Produkt-Baseline, während Dateien unter `specs/`, `plans/` und `audit/` einen Zeitpunkt-Entwurf oder eine Untersuchung beschreiben können.

## Aktuelle Produkt-Dokumentation

| Dokument | Zielgruppe | Zweck |
|---|---|---|
| [../README.md](../README.md) ([de](../README.de.md)) | Alle | Produkt-Überblick, Schnellstart, Sicherheits-Zusammenfassung und Repository-Karte |
| [FEATURES.md](FEATURES.md) ([de](FEATURES.de.md)) | Nutzer, Operatoren, Mitwirkende | aktuelles implementiertes Feature-Inventar, Anforderungen und Grenzen |
| [USER_GUIDE.md](USER_GUIDE.md) | Nutzer und Administratoren | tägliche Nutzung von Chat, Agenten, Projekten, Modulen und Betrieb |
| [ARCHITECTURE.md](ARCHITECTURE.md) ([de](ARCHITECTURE.de.md)) | Mitwirkende und Operatoren | Runtime-Architektur, Datenfluss, Speicherung und Erweiterungsmodell |
| [SECURITY_THREAT_MODEL.md](SECURITY_THREAT_MODEL.md) | Operatoren und Reviewer | Werte, Vertrauensgrenzen, Kontrollen und Restrisiken |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Nutzer und Operatoren | aktuelle unveröffentlichte Änderungen und Verweis auf veröffentlichte Releases |
| [COCKPITS.md](COCKPITS.md) | Nutzer und UI-Mitwirkende | Navigation und Cockpit-Karte |
| [../SPEC.md](../SPEC.md) | Maintainer und Mitwirkende | bindende Produkt-Baseline; Änderungen brauchen Maintainer-Freigabe |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Mitwirkende | Git-Workflow, Checks und Code-Konventionen |
| [../SECURITY.md](../SECURITY.md) | Security-Melder | Vulnerability-Meldung und unterstützte Versionen |
| [I18N.md](I18N.md) ([de](I18N.de.md)) | Mitwirkende | Sprach-Spiegel-Konvention für die Doku |

## Architektur-Deep-Dives

Die Subsystem-Dokumente in [`architecture/`](architecture/) ergänzen die High-Level-Architektur. Wenn ein älterer Deep-Dive mit aktuellem Code oder [FEATURES.md](FEATURES.md) kollidiert, vor dem Vertrauen gegen die Implementierung prüfen.

- [Architektur-Index](architecture/README.md)
- [Authentifizierung](architecture/auth.md)
- [Runner](architecture/runner.md)
- [Tools](architecture/tools.md)
- [Memory](architecture/memory.md)
- [Context-Compaction](architecture/compaction.md)
- [Media-Model-Integration](architecture/media-models.md)

## Betrieb und Deployment

- [Installer-Anleitung](../installer/README.md)
- [Compute-Node-Runbook](compute-node-runbook.md)
- [Ubuntu-26.04-Upgrade-Runbook](ubuntu-2604-upgrade-runbook.md)
- [Ollama-Provider-Anleitung](ollama-provider.md)
- [Node-Agent-Referenz](../node-agent/README.md)
- [Modul-Hub](https://github.com/hydrahive/hydrahive2-modules)

## Sicherheit

- [Threat Model](SECURITY_THREAT_MODEL.md)
- [Sicherheits-Härtungs-Notizen](security-hardening.md)
- [Dependency-Audit, August 2026](security-dependency-audit-2026-08.md)
- [Security-Policy](../SECURITY.md)

Security-Audits sind datierte Snapshots. Vor dem Vertrauen auf ihre Befunde die dokumentierten Checks erneut ausführen.

## Design-Aufzeichnungen und historische Dokumente

### `specs/`

Feature-Level-Designdokumente, Akzeptanzkriterien und Implementierungs-Verträge. Ihre Dateinamen identifizieren das Subsystem, aber nicht jedes Dokument ist ein lebendes Produkt-Handbuch. Sie helfen zu verstehen, warum ein Feature so entworfen wurde; [FEATURES.md](FEATURES.md) und der Code zeigen, was aktuell vorhanden ist.

Siehe [specs/README.md](specs/README.md).

### `plans/`

Implementierungs-Pläne während des Baus oder der Änderung eines Features. Ein abgeschlossener Plan ist historische Evidenz, keine Garantie, dass spätere Refactorings jeden Pfad oder Namen erhalten haben.

### `audit/`

Zeitpunkt-Implementierungs- und Gap-Audits. Das Datum im Dateinamen ist Teil des Ergebnisses und sollte beim Verweis mit zitiert werden.

### `compute-roadmap.md`

Vorausschauende Planung für das Compute-Subsystem. Sie ist nicht als Liste implementierter Features zu lesen.

## Dokumentations-Regeln

Bei Änderungen an HydraHive:

1. [FEATURES.md](FEATURES.md) für eine neue oder entfernte nutzersichtbare Fähigkeit aktualisieren;
2. [USER_GUIDE.md](USER_GUIDE.md) für geänderte Nutzer-/Admin-Workflows aktualisieren;
3. [ARCHITECTURE.md](ARCHITECTURE.md) oder den passenden `architecture/`-Deep-Dive aktualisieren, wenn Komponenten oder Datenfluss sich ändern;
4. [COCKPITS.md](COCKPITS.md) aktualisieren, wenn die Navigation sich ändert;
5. `SPEC.md` nur mit expliziter Maintainer-Freigabe und in einem separaten Commit ändern;
6. externe Abhängigkeiten, benötigte Credentials und Infrastruktur-Grenzen explizit kennzeichnen;
7. geplante Arbeit nicht als implementiert beschreiben.

Repository-Konventionen sind in [CONTRIBUTING.md](../CONTRIBUTING.md) definiert.
