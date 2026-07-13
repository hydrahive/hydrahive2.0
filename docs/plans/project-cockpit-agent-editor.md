# Plan: Vollständiger Agenten-Editor im Projekt-Cockpit

## Ziel

Das bisherige reduzierte Agenten-Overlay wird zum vollständigen Cockpit-Editor, ohne Navigation oder Abhängigkeit zur alten Settings-Seite.

## Dateien

- `core/src/hydrahive/api/routes/_agent_schemas.py` — erlaubt die Persistenz von `disabled_skills` im bestehenden Update-Endpunkt
- `core/tests/test_agents_api.py` — Regressionstest für deaktivierte Skills
- `frontend/src/features/agents/types.ts` — vollständiger Typ der änderbaren Agentenfelder
- `frontend/src/features/agents/api.ts` — verwendet den vollständigen Update-Typ
- `frontend/src/features/cockpit/ProjectCockpitPage.tsx` — remountet das Overlay sauber beim Agentenwechsel
- `frontend/src/features/cockpit/project/ProjectAgentEditOverlay.tsx` — Laden, Draft, Dirty-State, Speichern und Overlay-Shell
- `frontend/src/features/cockpit/project/ProjectAgentEditorTabs.tsx` — Cockpit-eigene Reiternavigation und vollständige Einstellungsinhalte
- `docs/specs/project-cockpit-agent-editor.md` — freigegebene Produktspezifikation
- `docs/plans/project-cockpit-agent-editor.md` — Implementierungs- und Verifikationsplan

## Bestehende Tests, die nicht brechen dürfen

- Frontend-Typecheck (`npx tsc -b`)
- ESLint (`npx eslint .`)
- Produktionsbuild (`npm run build`)
- Cockpit-Offline-Guard (`npm run check:cockpit-offline`)

Im Frontend ist kein Unit-Test-Runner konfiguriert. Deshalb wird die UI-Integration über Typecheck, Lint, Build und einen Browser-Smoke-Test verifiziert.

## Implementierungsreihenfolge

### Task 1: Vollständige Reiteroberfläche

- [x] `ProjectAgentEditorTabs.tsx` mit Übersicht, Modell, Prompt, Tools, Mail, Skills, Soul und Erweitert anlegen
- [x] Name/Status in der Cockpit-Übersicht editierbar machen
- [x] Bestehende Agent-Domänenkomponenten nutzen, aber keine Settings-Seite importieren
- [x] Typecheck ausführen

### Task 2: Vollständiges Laden und Speichern

- [x] Regressionstest für `disabled_skills` schreiben und rot bestätigen
- [x] `disabled_skills` in das bestehende Backend-Update-Schema aufnehmen und Test grün bestätigen
- [x] Overlay lädt Modellkatalog, Tools und MCP-Server zusätzlich zum Agenten und Systemprompt
- [x] Draft enthält alle Agentenfelder
- [x] Agentenfelder und Systemprompt werden gespeichert
- [x] Dirty-State und Verwerfen berücksichtigen alle zentral gespeicherten Felder
- [x] Parent-Liste erhält die aktualisierte Agent-Zusammenfassung

### Task 3: Verifikation

- [x] TypeScript-Typecheck grün
- [x] ESLint grün (keine Errors)
- [x] Frontend-Build grün
- [x] Cockpit-Offline-Guard grün
- [x] Browser-Smoke-Test: Overlay öffnet, Reiter sind sichtbar, Iterationen/Tokens und Soul-MD-Dateien sind erreichbar
- [x] HH2-Strukturreview durchführen

## Akzeptanzkriterien

- [x] Maximale Iterationen, maximale Tokens und Thinking-Budget sind im Projekt-Cockpit editierbar
- [x] Tools, MCP, Skills, Mail und Langzeitgedächtnis sind erreichbar
- [x] Systemprompt sowie `identity.md`, `behavior.md`, `background.md` sind erreichbar
- [x] Erweiterte Komprimierungsparameter sind erreichbar
- [x] Keine Abhängigkeit zu `features/settings/detail/AgentFormTabs.tsx`
- [x] Keine neue Backend- oder Berechtigungslogik

## Nicht in diesem Plan

- Alte Settings-Seiten entfernen
- Agenten löschen
- Backend-Schema erweitern
