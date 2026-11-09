# Plan: Compaction-Zuverlässigkeit

## Ziel

Automatische Compaction soll Retry-Stürme vermeiden, vorhandene Agent-Fallbacks nutzen, unnötige Chunks vermeiden und nach spätestens 900 Sekunden kontrolliert enden, ohne Subagent-/Delegationsstatus zu verändern.

## Dateien

- `core/src/hydrahive/compaction/_chunking.py` — kleine Reststücke weiterpacken
- `core/src/hydrahive/compaction/summarize.py` — sequenzieller Modell-Failover
- `core/src/hydrahive/compaction/compactor.py` — Gesamtzeitbudget und Cancellation-Telemetrie
- `core/src/hydrahive/db/compaction_events.py` — letztes Ereignis einer Session lesen
- `core/src/hydrahive/runner/_runner_iter.py` — Auto-Cooldown prüfen und Fallbacks weiterreichen
- `core/src/hydrahive/runner/runner.py` — bestehende Agent-Fallbackliste an Compaction geben
- `core/src/hydrahive/runner/_failover.py` — Verbindungsfehler als failoverfähig erkennen
- `core/tests/test_compaction_huge_messages.py` — Restpacking und Failover
- `core/tests/test_compaction_events_logging.py` — Latest-Event und Timeout-Telemetrie
- `core/tests/test_compaction_runner_reliability.py` — Cooldown, Weiterarbeiten und Fallback-Weitergabe
- `core/tests/test_failover_decision.py` — Connection-Fehlererkennung
- `docs/specs/compaction-reliability.md` — Vertrag und Grenzen
- `docs/architecture/compaction.md` — aktualisierte Laufzeitarchitektur

## Implementierungsreihenfolge

### Task 1: Restchunks packen
- [x] Test für überlange Zeile mit kleinem Rest plus Folgezeile schreiben und rot ausführen
- [x] `_hard_split` so ändern, dass nur volle Stücke sofort ausgegeben werden
- [x] Verlustfreiheit, Reihenfolge und Chunkgrenze grün prüfen

### Task 2: Sequenzieller Modell-Failover
- [x] Tests für 429, Connection-Fehler und nicht-retrybare Fehler schreiben und rot ausführen
- [x] Modellkette deduplizieren und ausschließlich konfigurierte Fallbacks verwenden
- [x] `_single_summarize` und Merge auf dieselbe Modellkette umstellen
- [x] Keine Parallelität einführen

### Task 3: Auto-Cooldown
- [x] Tests für aktiven Cooldown, Ablauf und erfolgreiche letzte Compaction schreiben
- [x] `latest_for_session` ergänzen
- [x] Runner überspringt nur automatische Compaction während fünf Minuten
- [x] Originalhistorie wird weiterhin ausgegeben; keine Delegation wird verändert

### Task 4: Gesamtzeitbudget
- [x] Timeout-Test mit blockiertem Summarizer schreiben und rot ausführen
- [x] `compact_session` mit 900-Sekunden-Wrapper versehen
- [x] Cancellation/Timeout als Fehlerereignis speichern
- [x] Sicherstellen, dass kein Compaction-Pointer persistiert wird

### Task 5: Integration und Review
- [x] Betroffene Tests gezielt ausführen
- [x] gesamte Core-Suite seriell ausführen (5.525 bestanden, 7 übersprungen)
- [ ] Ruff und Frontend-/Spec-Guards ausführen
- [ ] PR mit Vorher-/Nachher-Belegen erstellen
- [ ] Erst nach grüner CI mergen und kontrolliert ausrollen

## Nicht in diesem Plan

- Keine parallelen Chunk-Aufrufe
- Keine Änderung von AgentLink-/Handoff-Timeouts oder Delegationsstatus
- Keine neuen Provider oder automatisch erfundenen Modellnamen
- Keine Änderung der Compaction-Schwellenwerte
- Keine DB-Migration
