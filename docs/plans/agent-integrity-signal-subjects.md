# Plan: Agent Integrity — strukturierte Signal-Subjects

## Ziel

Integrity-Signale erhalten ein optionales, begrenztes `subject`: bei Completion-Claims die Claim-Art, bei Tool-/No-Progress-/Fehler-Signalen den Toolnamen. Die Admin-Metrik kann damit Fehlalarme nach Ursache aufschlüsseln, ohne Argumente, Ausgaben, Texte oder Identitäten zu speichern.

## Dateien

- `core/src/hydrahive/runner/integrity.py` — optionales sicheres Subject erzeugen und persistieren.
- `core/src/hydrahive/runner/integrity_metrics.py` — Subject-Aggregate bilden.
- `core/tests/test_runner_integrity.py` — Subject-, Begrenzungs- und Datenschutztests.
- `core/tests/test_integrity_metrics.py` — Claim- und Tool-Breakdowns testen.
- `core/tests/test_integrity_metrics_api.py` — erweiterten anonymen Response-Vertrag testen.
- `docs/specs/agent-integrity-layer.md` — Signalvertrag dokumentieren.

## Implementierungsreihenfolge

### Task 1: Sichere Subjects

- [x] RED-Tests für Claim-Art und Toolname schreiben.
- [x] Subject auf 80 Zeichen und sichere Zeichen begrenzen.
- [x] Ungültige Subjects als `other` klassifizieren.
- [x] Keine Argumente oder Details als Subject verwenden.

### Task 2: Aggregation

- [x] RED-Tests für `claim_counts`, `unverified_claim_counts` und `signal_subject_counts` schreiben.
- [x] Alte Signale ohne Subject weiter akzeptieren.
- [x] Cardinality und Zeilenmenge begrenzt halten.

### Task 3: Verifikation

- [x] Integrity-, Metrics-, API-, Auth- und Cache-Tests ausführen.
- [x] Ruff, Compile, HH- und Security-Review ausführen.
- [x] Prompt-Zuwachs weiterhin 0 bestätigen.
- [ ] PR, CI und Live-Smoke-Test abschließen.

## Akzeptanzkriterien

- [x] Admin-Metriken zeigen Claim-Arten und betroffene Toolnamen aggregiert.
- [x] Keine Rohargumente, Outputs, Texte oder Identifikatoren werden ergänzt.
- [x] Alte Phase-1-Metadaten bleiben auswertbar.
- [x] Kein Enforcement und kein zusätzlicher LLM-Aufruf.

## Vorab-Verifikation

- 69 kombinierte Signal-, Metrics-, API-, Cache- und Auth-Tests bestanden.
- Legacy-Signale ohne Subject und untrusted Subjects sind abgedeckt.
- Ruff, Compile, Dateigrößen- und Prompt-Isolationsprüfung ohne Befund.
