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

- [ ] RED-Tests für Dateiänderungen, Testbefehle und fehlgeschlagene Tools schreiben.
- [ ] Shell-Testbefehle mit Exit 0 erkennen.
- [ ] Befehle mit `|| true`, unsicheren Pipes oder maskiertem Exit-Code ablehnen.
- [ ] Keine Argumente oder Ausgaben persistieren.
- [ ] GREEN und Ruff ausführen.

### Task 2: Completion-Claims abgleichen

- [ ] RED-Tests für belegte und unbelegte Claims schreiben.
- [ ] Evidenztypen im bounded State halten.
- [ ] `unverified_completion_claim` nur als `observe`-Signal erzeugen.
- [ ] Negierte Claims weiterhin ignorieren.
- [ ] Snapshot enthält nur sortierte Evidenztypen.

### Task 3: Regression und Review

- [ ] Integrity-, Cache-, Runner-, Redaction- und Compaction-Tests ausführen.
- [ ] Stable-Prompt gegenüber `pre-agent-integrity-2026-09-23` unverändert bestätigen.
- [ ] Ruff, Compile, HH- und Security-Review ausführen.
- [ ] PR und CI abschließen.

## Akzeptanzkriterien

- [ ] Kein neuer LLM-Aufruf und kein Prompt-Zuwachs.
- [ ] Ein erfolgreiches `file_patch` belegt `implemented`, aber nicht `tested`.
- [ ] Nur ein erfolgreiches, nicht maskiertes Testkommando belegt `tested`.
- [ ] `fixed` benötigt Änderung plus bestandenen Test.
- [ ] Unbelegte Claims werden auditiert, aber nicht blockiert.
- [ ] Rohbefehle, Tool-Ausgaben und Nutzertext erscheinen nicht im Ledger.

## Nicht in diesem Plan

- Kein aktives Reality-Gate.
- Keine Bewertung freier fachlicher Wahrheiten.
- Kein LLM-as-a-Judge.
- Keine Wiederaufnahme alter Evidenz über unabhängige Nutzeraufträge hinweg.
