# Plan: Agent Integrity Layer — Phase 1

## Ziel

Ein beobachtender Integrity-State wird in den Runner integriert, ohne den Stable-Systemprompt zu vergrößern oder den Prompt-Cache zu destabilisieren. Phase 1 liefert belastbare Signale für semantische Tool-Wiederholungen, Fehlerketten, fehlenden Fortschritt, Provenienz und unbelegte Completion-Claims; aktive Enforcement-Entscheidungen bleiben bis zur Auswertung deaktiviert.

## Dateien

- `core/src/hydrahive/runner/integrity.py` — kleiner, deterministischer State- und Signalrechner ohne LLM-Aufruf.
- `core/src/hydrahive/runner/runner.py` — pro Run initialisieren und Iterations-/Tool-Signale einspeisen.
- `core/src/hydrahive/runner/_runner_tools.py` — Ergebnisstatus an den Integrity-State melden, ohne Tool-Rechte zu umgehen.
- `core/src/hydrahive/runner/system_prompt.py` — keine dynamischen Integrity-Daten ergänzen; Cache-Vertrag durch Test schützen.
- `core/tests/test_runner_integrity.py` — Unit-Tests für Normalisierung, Fingerprints, Claims, Fortschritt und Schwellenwerte.
- `core/tests/test_runner_cache.py` — Regressionstest: Integrity-State verändert stable nicht.
- `docs/specs/agent-integrity-layer.md` — Design und Phasenvertrag.

## Implementierungsreihenfolge

### Task 1: Deterministischer Integrity-State

- [ ] Tests für kanonische Tool-Signaturen und flüchtige Argumente schreiben.
- [ ] Test muss zunächst rot sein.
- [ ] `IntegrityState` mit bounded history und Ergebnis-Fingerprints implementieren.
- [ ] Tests für Fehlerketten, fehlenden Fortschritt und Completion-Claims ergänzen.
- [ ] Test grün und Datei unter ca. 200 Zeilen halten.
- [ ] Commit: `feat(runner): add phase one integrity signals`

### Task 2: Runner verdrahten

- [ ] Tests für State-Lifecycle über mehrere Iterationen schreiben.
- [ ] State pro Run erzeugen, nicht global teilen.
- [ ] Tool-Use und Tool-Ergebnisse nach Ausführung melden.
- [ ] Nur Telemetrie-/Warnsignale erzeugen; keine neue harte Blockierung.
- [ ] Bestehende Loop-, Max-Iteration- und Tool-Confirmation-Pfade unverändert lassen.
- [ ] Commit: `feat(runner): collect integrity signals per run`

### Task 3: Cache-Vertrag absichern

- [ ] Test für bytegleichen Stable-Prompt bei gleichem Input ergänzen.
- [ ] Test sicherstellen, dass Integrity-State nicht in stable/volatile injiziert wird.
- [ ] Promptgrößen-Baseline dokumentieren.
- [ ] Cache-Tests und Runner-Tests ausführen.
- [ ] Commit: `test(runner): protect prompt cache from integrity state`

### Task 4: Review und Baseline-Messung

- [ ] Core-Testmatrix für Runner, Cache, Tool-Dispatcher und Compaction ausführen.
- [ ] Ruff/Type- und Architekturchecks ausführen.
- [ ] Telemetrie-Signale anhand vorhandener Testläufe prüfen.
- [ ] `hh-review` und Security-Review durchführen.
- [ ] Spec-Akzeptanzkriterien für Phase 1 aktualisieren.
- [ ] Abschlusscommit: `docs(runner): record integrity phase one baseline`

## Akzeptanzkriterien

- [ ] Kein zusätzlicher LLM-Aufruf pro Turn.
- [ ] Stable-Prompt bleibt bytegleich und erhält keinen dynamischen Integrity-State.
- [ ] Tool-Signaturen ignorieren ausschließlich explizit erlaubte flüchtige Felder.
- [ ] Secret-Redaction bleibt vor Persistenz und vor Integrity-Fingerprints wirksam.
- [ ] Beobachtungsmodus verändert das bisherige Laufzeitverhalten nicht.
- [ ] Bisherige exakte Loop-Erkennung bleibt aktiv.
- [ ] Alle neuen Signale sind begrenzt und verursachen keinen unbounded Memory-Verbrauch.

## Nicht in diesem Plan

- Kein aktives semantisches Stoppen.
- Kein Reality-Gate, das Antworten bereits blockiert.
- Keine Datenbankmigration.
- Keine Änderung an Agenten-Soul-Templates außer nach separater Cache-Messung.
- Keine Frontend-Änderung.
