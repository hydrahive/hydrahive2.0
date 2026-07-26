# Plan: Anthropic-OAuth-Modellrefresh und Claude Opus 5

## Ziel

Der kanonische HydraHive-Modellkatalog lädt Anthropic-Modelle auch mit einem Claude-Code-/OAuth-Token live über `/v1/models`. Claude Opus 5 steht zusätzlich als sicherer Fallback mit vollständigen Laufzeitmetadaten bereit, sodass Buddy- und Agenten-Picker das Modell anzeigen und korrekt ausführen können.

## Dateien

- `core/src/hydrahive/llm/catalog.py` — tokenabhängige Anthropic-Authentifizierung für das Live-Listing.
- `core/src/hydrahive/llm/_catalog_data.py` — Opus-5-Fallback und Metadaten.
- `core/src/hydrahive/llm/_anthropic.py` — adaptive Effort-Unterstützung für Opus 5.
- `core/src/hydrahive/api/routes/llm_oauth.py` — Opus 5 als Default bei neuen Anthropic-OAuth-Konfigurationen.
- `core/src/hydrahive/llm/_pricing.py` — Opus-5-Preise für Telemetrie.
- `core/tests/test_llm_catalog.py` — OAuth-Header, Live-Erkennung und Fallback.
- `core/tests/test_reasoning_effort.py` — Opus-5-Effort-Pfad.
- `core/tests/test_llm_pricing.py` — Opus-5-Kostenlookup.

## Implementierungsreihenfolge

### Task 1: OAuth-Live-Listing

- [ ] Regressionstest: `sk-ant-oat` wird als Bearer mit Anthropic-OAuth-Headern gesendet.
- [ ] Test schlägt mit aktuellem `x-api-key`-Verhalten fehl.
- [ ] Auth-Header tokenabhängig erzeugen, ohne Tokens zu loggen.
- [ ] Live gelieferte unbekannte Modelle weiterhin automatisch durchreichen.

### Task 2: Opus-5-Fallback und Laufzeitmetadaten

- [ ] Tests für statische Sichtbarkeit, 1M-Kontext, Tool-Use und Anthropic-Familie ergänzen.
- [ ] `claude-opus-5` in Fallback und Metadata aufnehmen.
- [ ] Opus 5 dem adaptiven Effort-Pfad sowie den OAuth-Defaults hinzufügen.

### Task 3: Pricing und Gesamtverifikation

- [ ] Pricing-Test für Opus 5 ergänzen.
- [ ] Offizielle Preise $5/M Input und $25/M Output samt Cache-Raten hinterlegen.
- [ ] Fokussierte und vollständige Core-Tests sowie Ruff ausführen.
- [ ] Produktionskonfiguration read-only gegen Anthropic `/v1/models` prüfen; kein Deployment und kein Service-Neustart.

## Akzeptanzkriterien

- [ ] OAuth-Live-Fetch liefert ohne 401 die Anthropic-Modellliste.
- [ ] `claude-opus-5` erscheint in Registry und Buddy-Modellliste.
- [ ] Neue, noch nicht statisch bekannte Anthropic-Modelle werden live übernommen.
- [ ] Bei Providerfehlern bleibt Opus 5 über den statischen Fallback auswählbar.
- [ ] Opus 5 nutzt adaptive Thinking-/Effort-Stufen einschließlich `max`.
- [ ] Keine Secrets erscheinen in Logs, Tests oder Diffs.

## Nicht in diesem Plan

- Kein automatisches Umschalten bestehender Agenten auf Opus 5.
- Kein Deployment, Dateikopieren in die aktive Installation oder Service-Neustart.
- Keine Änderung an anderen Provider-Authentifizierungen.
