# Plan: Codex-OAuth erweitertes Kontextfenster

## Ziel

HydraHive nutzt für Codex-OAuth das accountbezogene maximale Kontextfenster und begrenzt die automatische Kompaktierung auf die vom Codex-Modell vorgegebene oder abgeleitete Obergrenze.

## Dateien

- `core/src/hydrahive/llm/catalog.py` — Codex-Katalogfelder normalisieren.
- `core/src/hydrahive/llm/registry.py` — Auto-Kompaktierungsgrenze im Live-Cache führen.
- `core/src/hydrahive/compaction/tokens.py` — Codex-Livewerte vor statischen Fallbacks auflösen.
- `core/src/hydrahive/compaction/compactor.py` — Modellgrenze in die gemeinsame Trigger-/Meter-Schwelle einbeziehen.
- `core/tests/test_catalog_live.py` — Codex-Kataloggrenzen testen.
- `core/tests/test_llm_registry.py` — Weitergabe und Cachezugriff testen.
- `core/tests/test_codex_context.py` — Live-vor-statisch und Fallback testen.
- `core/tests/test_compact_threshold_tokens.py` — 90-Prozent-Obergrenze und frühere Agentenschwelle testen.

## Implementierungsreihenfolge

### Task 1: Kataloggrenzen normalisieren
- [ ] Tests für `max_context_window` und explizite/abgeleitete Auto-Kompaktierung schreiben.
- [ ] Tests rot ausführen.
- [ ] Parser minimal erweitern.
- [ ] Tests grün ausführen.

### Task 2: Live-Metadaten in der Registry führen
- [ ] Registry-Test für `auto_compact_token_limit` schreiben.
- [ ] Test rot ausführen.
- [ ] `ModelEntry`, Merge und Cachezugriff erweitern.
- [ ] Test grün ausführen.

### Task 3: Codex-Livekontext auflösen
- [ ] Tests für Live-Priorität und statischen Fallback schreiben.
- [ ] Tests rot ausführen.
- [ ] Token-Auflösung ausschließlich für `openai-codex/*` erweitern.
- [ ] Tests grün ausführen.

### Task 4: Kompaktierungsobergrenze anwenden
- [ ] Tests für 872.000/784.800 und eine frühere 75-Prozent-Agentenschwelle schreiben.
- [ ] Tests rot ausführen.
- [ ] Gemeinsame Reserve-/Threshold-Berechnung erweitern.
- [ ] Tests grün ausführen.

### Task 5: Gesamtprüfung
- [ ] Betroffene Tests gemeinsam ausführen.
- [ ] Vollständige Core-Suite oder projektüblichen breiten Prüfpfad ausführen.
- [ ] Ruff/Formatprüfung ausführen.
- [ ] Architektur- und Security-Review durchführen.
- [ ] Git-Diff prüfen und committen.

## Akzeptanzkriterien

- [ ] OAuth-Livekatalog 872k wird statt statischem 372k verwendet.
- [ ] Auto-Kompaktierung spätestens bei 784.800 Tokens.
- [ ] Frühere Agentenschwellen bleiben wirksam.
- [ ] Kein OpenAI-API-Key-Aufruf.
- [ ] Keine Verhaltensänderung für Nicht-Codex-Provider.

## Prüfergebnis

- TDD: Die neuen Tests waren zunächst rot und sind nach der Implementierung grün.
- Betroffene und angrenzende Tests: 82 bestanden.
- Vollständige Core-Suite: 5.295 bestanden, 7 übersprungen; ein umgebungsbedingter Fehler wegen fehlendem `mutagen` in der wiederverwendeten Test-venv. Der betroffene Abhängigkeitstest lief mit der in `pyproject.toml` deklarierten Mutagen-Abhängigkeit isoliert grün (2 bestanden).
- Ruff: alle geänderten Python-Dateien ohne Befund.
- Echter OAuth-Katalog: 872.000 Kontext und 784.800 Auto-Kompaktierungsgrenze bestätigt; kein Inferenz- oder API-Key-Aufruf.

## Nicht in diesem Plan

- UI-Schalter für manuelle Kontextwerte.
- API-Key-Pfad.
- Änderung bestehender Agentenkonfigurationen.
- Belastungstest mit hunderttausenden real abgerechneten Tokens.
