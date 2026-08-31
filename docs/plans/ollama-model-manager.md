# Plan: Ollama-Modellmanager

## Ziel

Der bestehende Modellkatalog erhält eine Ollama-Ansicht mit offizieller Library, lokalem Installationszustand, llmfit-Hardwarebewertung und sicheren Installations-/Entfernungsaktionen.

## Dateien

- `core/src/hydrahive/llm/ollama_manager.py` — Ollama-Client, Library-Parser, llmfit-Adapter, Modell-Merge und Pull-Jobzustand
- `core/src/hydrahive/api/routes/llm_catalog.py` — Admin-Endpunkte und Request-Schemas
- `core/tests/test_ollama_manager.py` — Parser, Fit-Merge, Validierung, Fortschritt und Referenzschutz
- `core/tests/test_llm_catalog_ollama_api.py` — Auth- und API-Verträge
- `frontend/src/features/llm/api.ts` — TypeScript-Vertrag und API-Methoden
- `frontend/src/features/llm/CatalogPage.tsx` — Ollama-Ansicht, Varianten, Filter und Aktionen
- `frontend/src/i18n/locales/de/llm.json` — deutsche Texte
- `frontend/src/i18n/locales/en/llm.json` — englische Texte
- `installer/install.sh` und `installer/update.sh` — geprüfte llmfit-Installation beziehungsweise Aktualisierung
- `docs/specs/ollama-model-manager.md` — verbindlicher Funktions- und Sicherheitsvertrag

## Implementierungsreihenfolge

### Task 1: Read-only Ollama-Datenmodell

- [ ] Tests für Modellnamenvalidierung, Library-Familien-/Tag-Parsing und lokale `/api/tags`-/`/api/show`-Normalisierung schreiben
- [ ] Tests rot ausführen
- [ ] `ollama_manager.py` mit gecachtem, begrenztem Library-Fetch und konfiguriertem Ollama-Client implementieren
- [ ] llmfit-JSON tolerant auf stabile Felder normalisieren und über `ollama_name` mergen
- [ ] Tests grün ausführen
- [ ] Commit: `feat(llm): add Ollama catalog and hardware-fit adapter`

### Task 2: Pull/Delete-Verwaltung

- [ ] Tests für idempotente Pull-Jobs, NDJSON-Fortschritt, Fehlerzustände, ungültige Namen und Referenzkonflikte schreiben
- [ ] Tests rot ausführen
- [ ] In-Process-Pull-Registry und Upstream-Streaming implementieren
- [ ] Referenzen aus LLM-Konfiguration und Agentenkonfiguration vor Delete prüfen
- [ ] Admin-only API-Endpunkte in `llm_catalog.py` ergänzen
- [ ] API- und Unit-Tests grün ausführen
- [ ] Commit: `feat(llm): manage Ollama model lifecycle`

### Task 3: Katalogoberfläche

- [ ] TypeScript-Verträge für Library, Fit, Fähigkeiten und Pull-Jobs ergänzen
- [ ] Ollama-spezifische Ansicht mit Such-/Fit-/Capability-Filtern implementieren
- [ ] Varianten lazy laden
- [ ] Installationsfortschritt pollen; Erfolg aktualisiert den Katalog
- [ ] Delete-Bestätigung und Referenzkonflikte verständlich darstellen
- [ ] „Im Agent nutzen“ nur für installierte Chatmodelle anbieten
- [ ] DE-/EN-Texte ergänzen
- [ ] `npm run lint` und `npm run build` grün ausführen
- [ ] Commit: `feat(llm): add Ollama model manager UI`

### Task 4: llmfit-Auslieferung

- [ ] Installer-/Update-Verhalten für unterstützte Linux-Architekturen testen beziehungsweise statisch prüfen
- [ ] llmfit-Version pinnen, Release-Archiv nur nach SHA-256-Prüfung installieren
- [ ] Fehlschlag als Warnung behandeln, damit HydraHive weiter installierbar bleibt
- [ ] Runtime-Adapter bei fehlendem Binary weiterhin degradieren lassen
- [ ] Commit: `build(installer): install pinned llmfit binary`

### Task 5: Abschlussprüfung

- [ ] fokussierte Core-Tests ausführen
- [ ] vollständige Core-Test-Suite und Ruff ausführen
- [ ] Frontend-Lint, Admin-Visual-Check und Produktionsbuild ausführen
- [ ] Security-Audit: Auth, SSRF, Eingabevalidierung, Subprocess, Delete-Schutz und Fehlerredaktion
- [ ] `hh-review` ausführen und Findings beheben
- [ ] Code-Graph aktualisieren
- [ ] Branch pushen und PR erstellen

## Akzeptanzkriterien

- [ ] Der Katalog zeigt offizielle Ollama-Familien und lädt deren Tags bei Bedarf.
- [ ] Installierte Modelle zeigen lokale Größe, Quantisierung, Kontext und deklarierte Fähigkeiten.
- [ ] llmfit-Werte erscheinen, ohne dass ein llmfit-Ausfall den Katalog unbenutzbar macht.
- [ ] Ein Admin kann ein valides Modell installieren und den Fortschritt verfolgen.
- [ ] Ein Admin kann ein unreferenziertes installiertes Modell entfernen.
- [ ] Referenzierte Modelle werden mit HTTP 409 geschützt.
- [ ] Nicht-Admins können keine Verwaltungsendpunkte verwenden.
- [ ] Cloud-Provider und bestehende Agentenmodellwahl funktionieren unverändert.

## Nicht in diesem Plan

- Verwaltung anderer Modellserver oder Medienbackends
- freie Hugging-Face-/GGUF-Importe
- Ollama-Cloud-Accountverwaltung
- Capability-Tests mit Bildern oder Audio
- persistente Downloadjobs über Serverneustarts
