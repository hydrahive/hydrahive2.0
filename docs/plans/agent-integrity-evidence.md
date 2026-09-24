# Plan: Agent Integrity — Evidenzabgleich

## Ziel

Phase 1 erhält ein typisiertes Evidenz-Ledger. Erfolgreiche, eindeutig klassifizierbare Tool-Aktionen liefern Evidenz wie `artifact_changed` oder `tests_passed`. Positive Completion-Claims werden im Beobachtungsmodus gegen diese Evidenz geprüft; fehlende Nachweise erzeugen ausschließlich Audit-Signale, keine Blockierung und keinen zusätzlichen Prompttext.

## Dateien

- `core/src/hydrahive/runner/integrity_evidence.py` — konservative Tool-zu-Evidenz-Klassifikation und Claim-Anforderungen.
- `core/src/hydrahive/runner/integrity.py` — Evidenz im begrenzten Run-State sammeln und Claims abgleichen.
- `core/tests/test_runner_integrity_evidence.py` — Klassifikations-, Bypass- und Claim-Tests.
- `docs/specs/agent-integrity-layer.md` — Beobachtungsumfang und Grenzen dokumentieren.

## Implementierungsreihenfolge

### Task 1: Konservative Evidenzklassifikation

- [x] RED-Tests für Dateiänderungen, Testbefehle und fehlgeschlagene Tools schreiben.
- [x] Shell-Testbefehle mit Exit 0 erkennen.
- [x] Befehle mit `|| true`, unsicheren Pipes oder maskiertem Exit-Code ablehnen.
- [x] Keine Argumente oder Ausgaben persistieren.
- [x] GREEN und Ruff ausführen.

### Task 2: Completion-Claims abgleichen

- [x] RED-Tests für belegte und unbelegte Claims schreiben.
- [x] Evidenztypen im bounded State halten.
- [x] `unverified_completion_claim` nur als `observe`-Signal erzeugen.
- [x] Negierte Claims weiterhin ignorieren.
- [x] Snapshot enthält nur sortierte Evidenztypen.

### Task 3: Regression und Review

- [x] Integrity-, Cache-, Runner-, Redaction- und Compaction-Tests ausführen.
- [x] Stable-Prompt gegenüber `pre-agent-integrity-2026-09-23` unverändert bestätigen.
- [x] Ruff, Compile, HH- und Security-Review ausführen.
- [x] PR und CI abschließen.

## Akzeptanzkriterien

- [x] Kein neuer LLM-Aufruf und kein Prompt-Zuwachs.
- [x] Ein erfolgreiches `file_patch` belegt `implemented`, aber nicht `tested`.
- [x] Nur ein erfolgreiches, nicht maskiertes Testkommando belegt `tested`.
- [x] `fixed` benötigt Änderung plus bestandenen Test.
- [x] Unbelegte Claims werden auditiert, aber nicht blockiert.
- [x] Rohbefehle, Tool-Ausgaben und Nutzertext erscheinen nicht im Ledger.

## Nicht in diesem Plan

- Kein aktives Reality-Gate.
- Keine Bewertung freier fachlicher Wahrheiten.
- Kein LLM-as-a-Judge.
- Keine Wiederaufnahme alter Evidenz über unabhängige Nutzeraufträge hinweg.

## Verifikation

- 91 fokussierte Integrity-, Runner-, Cache-, Redaction- und Compaction-Tests bestanden.
- Ruff und Compile-Check ohne Befund.
- Backend-, Frontend- und Spec-Guard-CI bestanden.
- `system_prompt.py` gegenüber `pre-agent-integrity-2026-09-23` unverändert.
- Integrity bleibt im reinen Beobachtungsmodus.
