# Plan E2: Templates im Kern, API und Seite

Spec: `docs/specs/agent-templates.md` Kap. 5–7, 10. Voraussetzung: E1 gemergt.

## Ziel

Templates existieren als eigene Konfiguration, sind über die API (nur Admin schreibend) und den neuen
Reiter „Agenten-Templates“ der LLM-Seite pflegbar. Der Runner kann ein Template auflösen. Agenten
**ohne** `template` laufen unverändert weiter (Migration erst E3).

## Dateien

Kern
- `core/src/hydrahive/agents/templates/__init__.py` – öffentliche API: `list_templates`, `get`,
  `save`, `revert`, `resolve`, `ResolvedTemplate`.
- `core/src/hydrahive/agents/templates/_store.py` – Laden/Speichern `$HH_CONFIG_DIR/agent_templates.json`,
  atomar + Sperre (Muster `llm/_config.py`), Versionen/Verlauf.
- `core/src/hydrahive/agents/templates/_validation.py` – Pflichtfelder, Grenzen (Iterationen 1–250,
  Tokens 1–200.000, Timeout 30–3.600, overrun 0–100 %, cooldown 0–3.600), Kette 1–3 Einträge, keine
  Duplikate, Template-ID `^[a-z][a-z0-9-]{1,40}$`.
- `core/src/hydrahive/agents/templates/_defaults.py` – Start-Templates (Spec 6.1); Modell-IDs werden
  beim ersten Anlegen aus dem Katalog gewählt (verfügbare IDs bevorzugt), fehlende Stufe = leer.
- `core/src/hydrahive/agents/templates/_health.py` – Ampel je Template (alle Kettenmodelle im Katalog
  der eingetragenen Anbieter vorhanden? Sperrzeit aktiv?).
- `core/src/hydrahive/api/routes/agent_templates.py` – Routen (unten).
- `core/src/hydrahive/api/main.py` – Router einhängen.
- `core/src/hydrahive/runner/runner.py` – wenn `agent.template` gesetzt: Kette/Budget/TTL/Effort/
  Kompaktierung aus `resolve()` statt aus den Agent-Feldern.
- `core/src/hydrahive/runner/_call.py` – `cooldown_seconds` aus dem Template.

Frontend
- `frontend/src/features/llm/templates/` – `TemplatesTab.tsx` (Liste + Detail), `TemplateChain.tsx`,
  `TemplateBudget.tsx`, `TemplateReply.tsx`, `TemplateBindings.tsx`, `TemplateHistory.tsx`,
  `api.ts`, `types.ts`.
- `frontend/src/features/cockpit/admin/LlmOverlay.tsx` – Reiter-Leiste: Anbieter · Agenten-Templates ·
  Medien · Zuordnung · Verlauf. Die bisherigen Abschnitte wandern unter „Anbieter“ bzw. „Medien“.
- `frontend/src/features/llm/DefaultModelsSection.tsx` – Chat-/Lehren-Standard entfällt dort
  (→ System-Templates), Medien/Embedding bleiben.
- Modell-Auswahl: vorhandenen gruppierten Picker (`features/agents/_modelGroups.ts`) wiederverwenden,
  **ohne Limit**, alle Anbieter inkl. Ollama.
- i18n `de`/`en` (`llm.json`).

Tests
- `core/tests/test_agent_templates_store.py`, `test_agent_templates_validation.py`,
  `test_agent_templates_routes.py`, `test_agent_templates_resolve.py`, `test_runner_template.py`.
- Vitest: `TemplatesTab.test.tsx`, `TemplateChain.test.tsx`.

## API

| Methode | Pfad | Recht | Zweck |
|---|---|---|---|
| GET | `/api/agent-templates` | angemeldet | Liste (Nutzer: nur lesen) inkl. Ampel + Anzahl Gebundener |
| GET | `/api/agent-templates/{id}` | angemeldet | Detail |
| PUT | `/api/agent-templates/{id}` | **Admin** | Anlegen/Ändern → neue Revision; Antwort enthält betroffene Agenten |
| POST | `/api/agent-templates/{id}/preview` | **Admin** | Was würde sich ändern (ohne Speichern) |
| POST | `/api/agent-templates/{id}/test` | **Admin** | Kurze Frage durch jede Stufe, Ergebnis je Stufe |
| POST | `/api/agent-templates/{id}/revert/{revision}` | **Admin** | alte Revision zurückholen |
| DELETE | `/api/agent-templates/{id}` | **Admin** | nur wenn nichts gebunden ist (sonst 409) |
| GET | `/api/agent-templates/bindings` | **Admin** | alle Agenten/Module/Systemrollen mit Template oder „ungebunden“ |

Fehlertexte über Fehlercodes + i18n, keine rohen Ausnahmen.

## Reihenfolge

### T1: Speicher + Validierung
- [ ] Tests: anlegen, ändern erhöht Revision, alte Revision im Verlauf, `revert`, Grenzen,
      ungültige ID, Kette leer/zu lang/Duplikate, gleichzeitiges Schreiben (Sperre).
- [ ] RED → `_store.py`, `_validation.py` → GREEN. Commit.

### T2: Start-Templates
- [ ] Test: Leere Datei → beim ersten Laden 15 Templates (Spec 6.1); Failover jeweils anderer Anbieter
      als Primär; Notfall MiniMax M3.1 nur wenn im Katalog, sonst leer; Wiederholtes Laden legt nichts
      doppelt an.
- [ ] RED → `_defaults.py` → GREEN. Commit.

### T3: `resolve()`
- [ ] Tests: Agent mit `template` → Kette/Budget/Antwort aus Template; unbekanntes Template →
      Template `chat`-Fallback + Warnung im Log, kein Fehler; Agent ohne `template` → `None`
      (Runner nutzt alte Felder). Systemrollen per Name (`resolve_role("kompaktierung")`).
- [ ] RED → Umsetzung → GREEN. Commit.

### T4: Routen + Rechte
- [ ] Tests: Nutzer darf GET, bekommt 403 bei PUT/POST/DELETE; Admin darf alles; DELETE mit
      Gebundenen → 409; Preview listet betroffene Agenten; Test-Route ruft je Stufe mit Mock-LLM.
- [ ] RED → `api/routes/agent_templates.py` → GREEN. Commit.

### T5: Runner nutzt Template
- [ ] Test `test_runner_template.py`: Agent mit `template` → `stream_llm_call` bekommt Kette aus dem
      Template, `max_iterations`/`max_tokens`/`cache_ttl`/`reasoning_effort`/`compact_threshold_pct`
      aus dem Template; `model_override` der Sitzung hat weiter Vorrang (bewusste Nutzerwahl im Chat).
- [ ] RED → Umsetzung → GREEN, alle Runner-Tests grün. Commit.

### T6: Systemrollen
- [ ] Tests: Kompaktierung, Zahnfee, Lehren/Karten, Hilfe holen ihre Kette über `resolve_role`;
      ohne Template-Datei verhalten sie sich exakt wie heute (`default_model`, `zahnfee.json`,
      `lessons_model`).
- [ ] RED → Umsetzung in `compaction/_llm.py`, `zahnfee/runner.py`, `lessons/extract.py`,
      `cards/consolidate.py`, `helpdesk/_agent.py` → GREEN. Commit je Rolle.

### T7: Seite
- [ ] Vitest: Liste gruppiert + Ampel; Kette mit 3 Stufen, Warnung bei gleichem Anbieter; Budget mit
      Überschreitungs-Schalter; Speichern zeigt Vorschau der Betroffenen; Nutzer sieht alles
      schreibgeschützt; Verlauf + Zurückholen.
- [ ] Umsetzung nach Demo `_work/demo/llm-templates-demo.html`, Cockpit-Design, Dateien < 200 Zeilen.
- [ ] Commit je Komponente.

## Akzeptanzkriterien
- [ ] Admin legt Template an, ändert es, holt alte Revision zurück; Nutzer sieht nur.
- [ ] Agent mit `template` läuft mit Template-Werten; Agent ohne `template` exakt wie vorher.
- [ ] Systemrollen ohne Template-Datei unverändert.
- [ ] Test-Knopf zeigt je Stufe „antwortet / Fehler (Grund)“.
- [ ] `ruff`, `pytest`, `vitest`, `tsc` grün; `hh-review` ohne Befund.

## Nicht in diesem Plan
- Umstellung der bestehenden Agenten (E3), Budget bei Delegation/Überschreitung/Antwortformat (E4),
  Module (E5).
