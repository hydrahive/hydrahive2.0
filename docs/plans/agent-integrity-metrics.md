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

- [ ] RED-Tests mit synthetischen Integrity-Metadaten schreiben.
- [ ] Nur Metadaten selektieren, niemals `content`.
- [ ] Signaltypen und neue Evidenz je Sessionlauf aggregieren.
- [ ] Unbelegt-Quote berechnen.
- [ ] Zeitfenster und maximale Kandidatenzahl begrenzen.
- [ ] Defekte Metadaten zählen und überspringen.

### Task 2: Geschützter API-Endpunkt

- [ ] RED-Tests für unauthentifiziert, Nicht-Admin und Admin schreiben.
- [ ] `GET /api/system/integrity/summary?hours=24` ergänzen.
- [ ] `hours` auf 1–720 begrenzen.
- [ ] Keine Identifikatoren oder Rohdaten zurückgeben.

### Task 3: Verifikation

- [ ] Integrity-, DB-, Auth- und System-Route-Tests ausführen.
- [ ] Ruff, Compile, HH- und Security-Review ausführen.
- [ ] Stable-Prompt unverändert bestätigen.
- [ ] PR, CI und Live-Smoke-Test abschließen.

## Akzeptanzkriterien

- [ ] Endpunkt ist ausschließlich für Admins erreichbar.
- [ ] Antwort enthält keine Nachrichtentexte, Argumente, User-, Agent- oder Session-IDs.
- [ ] Abfrage ist auf 10.000 Kandidaten und maximal 720 Stunden begrenzt.
- [ ] Kumulative Snapshots zählen dieselbe Evidenz nicht mehrfach.
- [ ] Defekte Metadaten brechen die Auswertung nicht ab.
- [ ] Keine Prompt- oder LLM-Kosten.

## Nicht in diesem Plan

- Kein Frontend-Dashboard.
- Keine Einzelansicht von Sessions oder Benutzern.
- Kein aktives Enforcement.
- Keine Datenbankmigration.
