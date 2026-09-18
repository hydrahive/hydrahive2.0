# Plan: LLM-Katalog V2 — Multi-Node, Capability-Probes und Benchmarks

## Ziel

Der bestehende Katalog wird schrittweise zu einem multi-user-tauglichen, nodebezogenen Modellkatalog erweitert. Die erste Implementierungsschicht liefert einen stabilen Node-Vertrag, echte Capability-Probes und reproduzierbare Benchmarks, ohne direkte Browserzugriffe auf Modellserver.

## Bestehende Grundlagen

- `compute_nodes` ist die bestehende Registry für physische/local/agent Nodes und wird wiederverwendet statt eine zweite physische Node-Tabelle zu bauen.
- `llm.json` bleibt für Provider-/Modellkonfiguration zuständig; ein Provider erhält eine optionale `node_id`.
- Der bestehende Ollama-Katalog, Pull/Delete-Schutz und `registry` bleiben kompatibel.
- Probe- und Benchmark-Ergebnisse werden zunächst als kurzlebige, serverseitige Jobs behandelt; Persistenz über Neustarts ist ein separater Ausbau.

## Dateien

- `docs/specs/llm-catalog-v2.md` — verbindlicher Multi-Node-Vertrag (bereits erstellt)
- `core/src/hydrahive/llm/node_context.py` — Provider-/Node-Auflösung und sichere öffentliche Node-Metadaten
- `core/src/hydrahive/llm/capability_probe.py` — deklarierte/verifizierte Capability-Probes mit interner No-op-Funktion
- `core/src/hydrahive/llm/benchmark.py` — Jobzustand und tok/s-Auswertung
- `core/src/hydrahive/api/routes/llm_catalog.py` — Probe-/Benchmark-Endpunkte
- `core/src/hydrahive/api/routes/llm_catalog_ollama.py` — nodebezogene Ollama-Mutationsverträge
- `core/src/hydrahive/llm/ollama_manager.py` — Node-Metadaten und Fit-Quelle im Katalog
- `core/tests/test_llm_catalog_v2.py` — Unit-/API-Verträge, Auth, Scope und Berechnungen
- `core/tests/test_ollama_manager.py` — Regressionen für nodebezogenen Merge
- `frontend/src/features/llm/ollamaApi.ts` — Node-/Capability-/Benchmark-Typen
- `frontend/src/features/llm/OllamaCatalog.tsx` — Node- und Verifikationsanzeige
- `frontend/src/features/llm/OllamaModelList.tsx` — Capability-Status und tok/s-Anzeige
- `frontend/src/features/llm/api.ts` — generische Katalogtypen

## Implementierungsreihenfolge

### Task 1: Node-Vertrag ohne Sonder-IP

- [ ] Tests für Provider ohne `node_id`, lokalen Node und unbekannten Node schreiben
- [ ] `node_context.py` implementieren: `node_id` ableiten, Compute-Node lesen, Endpoint nie zurückgeben
- [ ] Katalogantwort um `node_id`, `node_name`, `node_status`, `hardware_source` ergänzen
- [ ] Remote-Fit bleibt `unknown`, wenn kein Fit-Agent auf dem Node vorhanden ist
- [ ] fokussierte Tests grün
- [ ] Commit: `feat(llm): add node context to model catalog`

### Task 2: Deklarierte Capability-Probe

- [ ] Tests für `declared`, `verified`, `failed`, `unknown` und Digest-/Probe-Version-Cache schreiben
- [ ] internes ungefährliches Probe-Tool implementieren, das keine User-Tools, Dateien, Shell oder Netzwerkziele erreicht
- [ ] echten Chat-/Tool-Call über den bestehenden Runner-Providerpfad ausführen
- [ ] Ergebnis redigiert und modell-/nodebezogen zurückgeben
- [ ] nur Admin darf Probejobs starten; Polling darf berechtigte Nutzer ohne Secretzugriff erlauben
- [ ] fokussierte Tests inklusive falschem `/api/show`-Capability-Claim grün
- [ ] Commit: `feat(llm): verify model capabilities with safe probes`

### Task 3: Benchmarkjob mit echten tok/s

- [ ] Tests für Prompt-/Output-Tokens, Nullwerte, Timeout, Fehlerstatus und Job-Idempotenz schreiben
- [ ] Hintergrundjob mit begrenzter Laufzeit und maximaler Outputgröße implementieren
- [ ] Prompt-tok/s und Output-tok/s getrennt ausweisen; Wall-Clock nicht als tok/s ausgeben
- [ ] Ergebnis an Node, Modell-Digest und Benchmark-Version binden
- [ ] kein automatischer Start bei Seitenaufruf oder Pull
- [ ] fokussierte Tests grün
- [ ] Commit: `feat(llm): add node-scoped model benchmarks`

### Task 4: Ollama-Lifecycle auf Nodes

- [ ] Tests für Pull/Delete mit `node_id`, offline Node, Referenzschutz und Berechtigungsfehler schreiben
- [ ] vorhandene Ollama-Routen um Node-Auflösung erweitern
- [ ] bestehende Legacy-Routen auf den konfigurierten Standard-Node abbilden
- [ ] Pull/Delete niemals mit frei gelieferter URL ausführen
- [ ] fokussierte API-Tests grün
- [ ] Commit: `feat(llm): scope Ollama lifecycle to execution nodes`

### Task 5: Frontend

- [ ] Node-Auswahl und Statuskarten ergänzen
- [ ] deklarierte/verifizierte/fehlgeschlagene Capabilities getrennt anzeigen
- [ ] Probe- und Benchmarkaktionen mit Polling und Fehlerzuständen ergänzen
- [ ] Fit-Quelle und Zeitstempel anzeigen
- [ ] bestehende Installieren/Löschen/Agent-nutzen-Flows erhalten
- [ ] `npm run lint` und `npm run build` grün
- [ ] Commit: `feat(llm): expose node and verification data in catalog`

### Task 6: Abschlussprüfung

- [ ] Core-Fokustests, vollständige Core-Suite und Ruff
- [ ] Frontend-Lint und Produktionsbuild
- [ ] Security-Audit: Auth, SSRF, Node-Scope, Secret-Redaktion, Rate-/Job-Limits
- [ ] `hh-review` und Code-Graph-Refresh
- [ ] Live-Smoke auf mindestens einem lokalen und einem Remote-Ollama-Node
- [ ] Push und PR beziehungsweise kontrollierter Main-Deploy

## Akzeptanzkriterien

- Zwei Nodes mit gleichem Modellnamen werden getrennt katalogisiert.
- Kein Remote-Modell erhält Hardware-Fit vom Core-Host.
- `/api/show`-Capabilities erscheinen nur als `declared`, bis eine echte Probe erfolgreich war.
- Eine erfolgreiche Tool-Probe enthält einen echten nativen Tool-Call und den internen Probe-Dispatcher-Erfolg.
- Benchmarks liefern Prompt-/Output-tok/s und sind node-/digestbezogen.
- Pull/Delete bleiben admin-geschützt, validieren Modellnamen und prüfen Referenzen.
- Bestehende Cloud-Provider und die bisherige Modellwahl bleiben kompatibel.

## Nicht in diesem Plan

- Persistente Probe-/Benchmarkhistorie über Serverneustarts
- automatische Modell-Downloads aufgrund eines Fits
- freie Hugging-Face-/GGUF-Imports
- ComfyUI-, Bild-, Video- oder Musikmodellverwaltung
- direkter Browserzugriff auf Ollama oder beliebige Nutzer-URLs
