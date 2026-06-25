# HydraHive2 — Dokumentations-Index

Eine Übersicht über die vorhandene Doku, sortiert nach Ziel.

## "Ich will das System nutzen / installieren"

→ Hauptverzeichnis [README.md](../README.md) — Quick-Start, Konfiguration, Sicherheit
→ [installer/README.md](../installer/README.md) — Installations-Details
→ [USER_GUIDE.md](USER_GUIDE.md) — Bedienung aus Nutzersicht

## "Ich will beitragen / Code ändern"

In dieser Reihenfolge:

1. [CONTRIBUTING.md](../CONTRIBUTING.md) — Git-Workflow, Tests, Konventionen, Arbeitsregeln
2. [SPEC.md](../SPEC.md) — Produkt-Spezifikation (heilig, nicht ohne OK ändern)
3. [ARCHITECTURE.md](ARCHITECTURE.md) — Architektur-Überblick, wo liegt was

## "Ich will verstehen wie ein Subsystem funktioniert"

`docs/architecture/` — Subsystem-Deep-Dives:

- [memory.md](architecture/memory.md) — Memory v2 Pipeline (Observation → Compress → Crystallize → Lessons → Context-Injection)
- [runner.md](architecture/runner.md) — Tool-Loop, Streaming, Provider-Switch, Token-Counts
- [compaction.md](architecture/compaction.md) — `firstKeptEntryId`-Pointer, hierarchisches Merging
- [auth.md](architecture/auth.md) — JWT, API-Keys, Roles, OAuth-Flow
- [tools.md](architecture/tools.md) — Tool-System
- [media-models.md](architecture/media-models.md) — Media-Modell-Konfiguration

## Pflege

Wer welche Datei ändert, siehe [CONTRIBUTING.md](../CONTRIBUTING.md#doku-pflege).
SPEC.md wird nur mit explizitem OK geändert — standalone-Commit erforderlich
(Pre-Commit-Hook erzwingt das).
