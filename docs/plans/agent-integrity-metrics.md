# Plan: Agent Integrity — Beobachtungsmetriken

## Ziel

Admins erhalten eine aggregierte, datensparsame Auswertung des Integrity-Beobachtungsmodus. Die API liefert Signalzahlen, neu beobachtete Evidenztypen und die Quote unbelegter Completion-Claims, aber keine Nachrichteninhalte, Toolargumente, Session-IDs oder Benutzerdaten.

## Dateien

- `core/src/hydrahive/runner/integrity_metrics.py` — begrenzte Aggregation aus Message-Metadaten.
- `core/src/hydrahive/api/routes/system_admin.py` — Admin-only Read-Endpunkt mit validiertem Zeitfenster.
- `core/tests/test_integrity_metrics.py` — Aggregations-, Datenschutz-, Limit- und Fehlerdatentests.
- `core/tests/test_integrity_metrics_api.py` — Auth-, Parameter- und Response-Tests.
- `docs/specs/agent-integrity-layer.md` — Metrikvertrag dokumentieren.

## Implementierungsreihenfolge

### Task 1: Aggregator

- [x] RED-Tests mit synthetischen Integrity-Metadaten schreiben.
- [x] Nur Metadaten selektieren, niemals `content`.
- [x] Signaltypen und neue Evidenz je Sessionlauf aggregieren.
- [x] Unbelegt-Quote berechnen.
- [x] Zeitfenster und maximale Kandidatenzahl begrenzen.
- [x] Defekte Metadaten zählen und überspringen.

### Task 2: Geschützter API-Endpunkt

- [x] RED-Tests für unauthentifiziert, Nicht-Admin und Admin schreiben.
- [x] `GET /api/system/integrity/summary?hours=24` ergänzen.
- [x] `hours` auf 1–720 begrenzen.
- [x] Keine Identifikatoren oder Rohdaten zurückgeben.

### Task 3: Verifikation

- [x] Integrity-, DB-, Auth- und System-Route-Tests ausführen.
- [x] Ruff, Compile, HH- und Security-Review ausführen.
- [x] Stable-Prompt unverändert bestätigen.
- [ ] PR, CI und Live-Smoke-Test abschließen.

## Akzeptanzkriterien

- [x] Endpunkt ist ausschließlich für Admins erreichbar.
- [x] Antwort enthält keine Nachrichtentexte, Argumente, User-, Agent- oder Session-IDs.
- [x] Abfrage ist auf 10.000 Kandidaten und maximal 720 Stunden begrenzt.
- [x] Kumulative Snapshots zählen dieselbe Evidenz nicht mehrfach.
- [x] Defekte Metadaten brechen die Auswertung nicht ab.
- [x] Keine Prompt- oder LLM-Kosten.

## Nicht in diesem Plan

- Kein Frontend-Dashboard.
- Keine Einzelansicht von Sessions oder Benutzern.
- Kein aktives Enforcement.
- Keine Datenbankmigration.

## Vorab-Verifikation

- 71 kombinierte Metrics-, Integrity-, Cache-, Auth- und Admin-Tests bestanden.
- Isolierte DB-Tests zweimal hintereinander bestanden.
- Ruff, Compile- und Prompt-Isolationsprüfung ohne Befund.
- Sechs während RED/GREEN entstandene, eindeutig synthetische Live-Test-Sessions gezielt entfernt; verbleibend: 0.
