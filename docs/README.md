# HydraHive2 — Dokumentations-Index

Eine Übersicht über die vorhandene Doku, sortiert nach Ziel.

## "Ich will das System nutzen / installieren"

→ Hauptverzeichnis [README.md](../README.md) — Quick-Start, Konfiguration, Sicherheit
→ [installer/README.md](../installer/README.md) — Installations-Details

## "Ich will beitragen / Code ändern"

In dieser Reihenfolge:

1. [CLAUDE.md](../CLAUDE.md) — **verbindliche Arbeitsregeln** (Datei-Größen, Co-location, was-nicht-zu-tun)
2. [CONTRIBUTING.md](../CONTRIBUTING.md) — Git-Workflow, Tests, Konventionen
3. [STRUCTURE.md](STRUCTURE.md) — Verzeichnis-Übersicht, wo liegt was
4. [SPEC.md](../SPEC.md) — Produkt-Spezifikation (heilig, nicht ohne Tills OK ändern)
5. [HANDOVER.md](HANDOVER.md) — aktueller Session-State, was offen ist

## "Ich will verstehen wie ein Subsystem funktioniert"

`docs/architecture/` — Subsystem-Deep-Dives:

- [memory.md](architecture/memory.md) — Memory v2 Pipeline (Observation → Compress → Crystallize → Lessons → Context-Injection)
- [runner.md](architecture/runner.md) — Tool-Loop, Streaming, Provider-Switch, Token-Counts
- [compaction.md](architecture/compaction.md) — `firstKeptEntryId`-Pointer, hierarchisches Merging
- [auth.md](architecture/auth.md) — JWT, API-Keys, Roles, OAuth-Flow

## "Ich will Tests schreiben / Test-Status prüfen"

- [TESTING_STATUS.md](TESTING_STATUS.md) — aktueller Stand (243 Tests, Coverage-Matrix)
- [TEST_DEEP_DIVE.md](TEST_DEEP_DIVE.md) — historische Analyse (2026-05-06, vor dem Test-Aufbau)
- [TEST_CHECKLIST.md](TEST_CHECKLIST.md) — historisches Tracking (während Test-Aufbau)

## "Ich greife eine alte KI-Session wieder auf"

- [HANDOVER.md](HANDOVER.md) zuerst lesen
- dann [SPEC.md](../SPEC.md) wenn unklar was gebaut werden soll
- dann konkret nach offenen Tasks fragen

## Pflege

Wer welche Datei ändert, siehe [CONTRIBUTING.md](../CONTRIBUTING.md#doku-pflege).
SPEC.md und CLAUDE.md sind Tills Domäne — nie ohne explizites OK ändern,
standalone-Commit erforderlich (Pre-Commit-Hook erzwingt).
