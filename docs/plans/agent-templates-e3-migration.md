# Plan E3: Bestehende Agenten an Templates binden (harte Bindung)

Spec: `docs/specs/agent-templates.md` Kap. 5, 6, 10. Voraussetzung: E2 live.

## Ziel

Jeder Agent hat ein `template`. Modell, Fallback und Budget sind im Agenten nicht mehr einstellbar.
Neue Agenten bekommen beim Anlegen automatisch ein Template.

## Dateien

- `core/src/hydrahive/agents/templates/_migrate.py` – Zuordnungsvorschlag + Anwenden + Sicherung.
- `core/src/hydrahive/api/routes/agent_templates.py` – `GET /bindings/proposal`, `POST /bindings/apply`
  (Admin).
- `core/src/hydrahive/agents/config.py` – `create(..., template=…)`; `update`: Felder
  `llm_model, fallback_models, max_iterations, max_tokens, handoff_timeout_seconds, reasoning_effort,
  compact_threshold_pct, cache_ttl, compact_model` werden bei gebundenem Agenten **abgelehnt**
  (Fehlercode `agent_bound_to_template`).
- `core/src/hydrahive/agents/_managed.py` – `FREE` um `template` erweitern; Modell-/Budgetfelder
  entfallen aus `FREE` (Module wählen das Template, nicht das Modell).
- Anlege-Stellen mit Default-Template: `buddy/__init__.py` (→ `buddy`), `projects/config.py`
  (→ `projekt-master`), `tools/create_specialist.py` (Pflichtfeld `template`, Auswahl aus Liste),
  `helpdesk/_agent.py` (→ `hilfe`), `api/routes/agents.py` (`template` Pflicht, Default nach Typ),
  `agents/external_instances.py`, `api/routes/mcp.py` (Typ-Default).
- `tools/create_specialist.py`, `tools/configure_specialist.py` – Schema: `template` statt `llm_model`,
  `fallback_models`, `max_*`.
- Frontend `features/agents/_ModelTab.tsx`, `_AgentModelPicker.tsx`, `_FallbackModelsSelector.tsx`,
  `CompactionSection.tsx`, `NewAgentDialog.tsx` – bei gebundenem Agenten nur Template-Auswahl +
  Link „Template öffnen“, Werte schreibgeschützt angezeigt.
- Frontend `features/llm/templates/BindingsTab.tsx` – Reiter „Zuordnung“: Vorschlag prüfen,
  einzeln ändern, anwenden.
- Tests: `test_agent_templates_migrate.py`, `test_agent_config_bound.py`, `test_create_specialist_template.py`,
  Vitest für `_ModelTab` und `BindingsTab`.

## Zuordnungsregeln (Vorschlag, Admin bestätigt)

| Bedingung | Template |
|---|---|
| `type == master`, Name endet auf „Buddy“ | buddy |
| `type == master`, Name endet auf „Assistant“ | assistant |
| `type == master`, sonst | buddy |
| `type == project` | projekt-master |
| specialist, Name enthält `review` / `auditor` | reviewer |
| specialist, Name enthält `security` | security |
| specialist, Name enthält `frontend` | frontend |
| specialist, Name enthält `backend` / `engineer` / `storage` | backend |
| specialist, Name enthält `test` / `verifier` | reviewer |
| specialist, sonst | recherche |
| `managed_by` gesetzt | Template des Moduls (E5), bis dahin `modul-schnell` |

Jede Zeile zeigt: Agent, Besitzer, bisheriges Modell/Budget, vorgeschlagenes Template, Unterschiede
(z. B. „Iterationen 250 → 96“). Unsichere Treffer (Regel „sonst“) sind markiert.

## Reihenfolge

### T1: Vorschlag
- [ ] Tests: Regeln oben mit echten Namen aus .4 (Fixture aus den 41 Configs, ohne Prompts);
      `managed_by` erkannt; Ergebnis stabil sortiert.
- [ ] RED → `_migrate.propose()` → GREEN. Commit.

### T2: Anwenden mit Sicherung
- [ ] Tests: `apply(proposal)` schreibt Sicherung aller betroffenen Configs nach
      `$HH_DATA/backups/agent-templates/<zeitstempel>/`, setzt `template`, lässt alte Felder
      **unverändert in der Datei** (Rückweg), ist idempotent, bricht bei Schreibfehler ohne Teil-
      zustand ab (erst alle Sicherungen, dann schreiben, bei Fehler zurückkopieren).
- [ ] `undo(zeitstempel)` stellt die Sicherung wieder her.
- [ ] RED → Umsetzung → GREEN. Commit.

### T3: Harte Bindung in `agents/config.py`
- [ ] Tests: gebundener Agent – Änderung an `llm_model` u. a. → `agent_bound_to_template`; Änderung
      von `template` erlaubt; ungebundener Agent wie bisher; `_managed.guard` lässt `template` frei.
- [ ] RED → Umsetzung → GREEN, `test_agent_managed.py` angepasst. Commit.

### T4: Anlegen mit Template
- [ ] Tests je Anlege-Stelle (Buddy, Projekt, Spezialist per Tool und per Route, Hilfe, extern, MCP):
      neues Agent-JSON enthält passendes `template`.
- [ ] RED → Umsetzung → GREEN. Commit je Stelle.

### T5: Werkzeuge der Agenten
- [ ] Tests: `create_specialist` verlangt `template` aus der Liste, lehnt `llm_model` ab;
      `configure_specialist` kann nur `template` wechseln.
- [ ] RED → Umsetzung → GREEN. Commit.

### T6: Oberfläche
- [ ] Vitest: Agent-Editor zeigt bei gebundenem Agenten Template-Auswahl + schreibgeschützte Werte;
      Reiter „Zuordnung“ zeigt Vorschlag, erlaubt Einzeländerung, „Anwenden“ fragt mit Anzahl nach.
- [ ] Umsetzung, i18n de/en. Commit.

### T7: Betrieb
- [ ] Auf hydratest: Vorschlag ansehen, anwenden, Stichprobe 3 Agenten (Buddy, Projekt, Spezialist)
      chatten bzw. delegieren, `undo` testen.
- [ ] Auf .2: Vorschlag als Tabelle an Till, **erst nach OK** anwenden.

## Akzeptanzkriterien
- [ ] Nach `apply` haben alle Agenten ein `template`, Modell/Budget kommen nur noch aus dem Template.
- [ ] `undo` stellt den Zustand vor `apply` exakt her (Dateivergleich).
- [ ] Neue Agenten (alle Wege) sind sofort gebunden.
- [ ] Nutzer können am Agenten kein Modell/Budget mehr setzen, Admins nur über das Template.

## Nicht in diesem Plan
- Entfernen der alten Felder aus den Dateien (E7). Budget bei Delegation (E4). Module (E5).
