# Plan: Harness Doctor V1

## Dateien

- `core/src/hydrahive/harness_doctor/{models,collector,rules}.py` — Daten sammeln und transparent bewerten
- `core/src/hydrahive/api/routes/harness_doctor.py` — admin-only Read-Route
- `core/src/hydrahive/api/main.py` — Router registrieren
- `core/tests/test_harness_doctor_{rules,api}.py` — Regeln, Auth, Datenschutz, Read-only
- `frontend/src/features/cockpit/admin/HarnessDoctorPanel.tsx` — Anzeige
- `frontend/src/features/cockpit/admin/harnessDoctorApi.ts` — Typen/API
- `frontend/src/features/cockpit/admin/systemTabs.ts` und `SystemOverlay.tsx` — Admin-Reiter
- passende Frontendtests und i18n-Texte

## Reihenfolge

1. Pure Regeltests rot schreiben; Score-Engine implementieren.
2. Collector mit lokalen Agent-/Projekt-/Skill-/Tooldaten und aggregierter DB-Telemetrie implementieren.
3. Admin-Route, Auth- und Datenschutztests.
4. System-Reiter, API-Typen und UI-Tests.
5. Core-/Frontend-Gesamttests, HH-Review, PR, grüne CI, kontrollierter Rollout.

## Nicht enthalten

Keine Auto-Fixes, keine Taskanlage, keine Remote-CI-/MCP-Abfrage, keine Inhalte/Secrets, keine DB-Migration.
