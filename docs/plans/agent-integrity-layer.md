# Plan: Agent Integrity Layer — Phase 1

## Ziel

Ein beobachtender Integrity-State wird in den Runner integriert, ohne den Stable-Systemprompt zu vergrößern oder den Prompt-Cache zu destabilisieren. Phase 1 liefert belastbare Signale für kanonisch äquivalente Tool-Wiederholungen, Fehlerketten, fehlenden Fortschritt, Provenienz und unbelegte Completion-Claims; aktive Enforcement-Entscheidungen bleiben bis zur Auswertung deaktiviert.

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

- [x] Tests für kanonische Tool-Signaturen und flüchtige Argumente schreiben.
- [x] Test muss zunächst rot sein.
- [x] `IntegrityState` mit bounded history und Ergebnis-Fingerprints implementieren.
- [x] Tests für Fehlerketten, fehlenden Fortschritt und Completion-Claims ergänzen.
- [x] Test grün und Datei unter ca. 200 Zeilen halten.
- [x] Commit: `feat(runner): add phase one integrity signals`

### Task 2: Runner verdrahten

- [x] Tests für State-Lifecycle über mehrere Iterationen schreiben.
- [x] State pro Run erzeugen, nicht global teilen.
- [x] Tool-Use und Tool-Ergebnisse nach Ausführung melden.
- [x] Nur Telemetrie-/Warnsignale erzeugen; keine neue harte Blockierung.
- [x] Bestehende Loop-, Max-Iteration- und Tool-Confirmation-Pfade unverändert lassen.
- [x] Commit: `feat(runner): collect integrity signals per run`

### Task 3: Cache-Vertrag absichern

- [x] Test für bytegleichen Stable-Prompt bei gleichem Input ergänzen.
- [x] Test sicherstellen, dass Integrity-State nicht in stable/volatile injiziert wird.
- [x] Promptgrößen-Baseline dokumentieren.
- [x] Cache-Tests und Runner-Tests ausführen.
- [x] Cache-Schutztests sind im Runner-Wiring-Commit `84a36360` enthalten.

### Task 4: Review und Baseline-Messung

- [x] Core-Testmatrix für Runner, Cache, Tool-Dispatcher und Compaction ausführen.
- [x] Ruff/Type- und Architekturchecks ausführen.
- [x] Telemetrie-Signale anhand vorhandener Testläufe prüfen.
- [x] `hh-review` und Security-Review durchführen.
- [x] Spec-Akzeptanzkriterien für Phase 1 aktualisieren.
- [x] Abschlusscommit: `docs(runner): record integrity phase one baseline`

## Akzeptanzkriterien

- [x] Kein zusätzlicher LLM-Aufruf pro Turn.
- [x] Stable-Prompt bleibt bytegleich und erhält keinen dynamischen Integrity-State.
- [x] Tool-Signaturen ignorieren ausschließlich explizit erlaubte flüchtige Felder.
- [x] Roh-Secrets erscheinen nicht in persistierten Integrity-Metadaten; Tool-Ergebnisse werden erst nach zentraler Redaction ausgewertet.
- [x] Beobachtungsmodus verändert das bisherige Laufzeitverhalten nicht.
- [x] Bisherige exakte Loop-Erkennung bleibt aktiv.
- [x] Alle neuen Signale sind begrenzt und verursachen keinen unbounded Memory-Verbrauch.

## Nicht in diesem Plan

- Kein aktives semantisches Stoppen.
- Kein Reality-Gate, das Antworten bereits blockiert.
- Keine Datenbankmigration.
- Keine Änderung an Agenten-Soul-Templates außer nach separater Cache-Messung.
- Keine Frontend-Änderung.

## Verifikation Phase 1

- Baseline-Tag: `pre-agent-integrity-2026-09-23` (`4b855ee2`).
- Feature-Commits: `a86b0ef6`, `84a36360`, `e5e7cdae`.
- Vollständige Core-Suite: **2.213 Tests bestanden**.
- Fokussierte Integrity-/Cache-Suite: **31 Tests bestanden**.
- Ruff: alle geänderten Python-Dateien ohne Befund.
- Import-/Compile-Check: erfolgreich.
- Stable-Prompt-Code gegenüber dem Baseline-Tag: unverändert.
- Kontroll-Baseline: `stable_chars=62`, `volatile_chars=103` für den deterministischen Test-Prompt; Integrity erhöht beide Werte um **0 Zeichen**.
- Integrity-Metadaten werden von `to_anthropic_messages()` nicht an das Modell übertragen.
