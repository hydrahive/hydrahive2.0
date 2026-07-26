# Plan: Buddy-Einstellungscockpit

## Ziel

`/buddy/settings` wird ein vollständiges eigenständiges Cockpit für den persönlichen Buddy. Backend und UI decken Persönlichkeit, Kontext, Modelle, Tools/MCP, Skills, Mail und Advanced ab, ohne den Legacy-Agenteneditor einzubetten.

## Dateien

### Backend
- `core/src/hydrahive/buddy/_config.py` — vollständige owner-gebundene Buddy-Konfiguration lesen/schreiben.
- `core/src/hydrahive/api/routes/buddy.py` — validiertes Patch-Schema erweitern.
- `core/src/hydrahive/api/routes/skills.py` — optional ungefilterte effektive Skills liefern.
- `core/tests/test_buddy_smoke.py` — Read-/Patch-Vertrag und Owner-Isolation.
- `core/tests/test_skills_api.py` oder passende bestehende Skill-Testdatei — deaktivierte Skills mit `include_disabled`.

### Frontend
- `frontend/src/features/buddy/BuddySettingsPage.tsx` — Cockpit-Shell, Navigation, Draft-/Save-Flow.
- `frontend/src/features/buddy/api.ts` — vollständige Typen und Skill-Query.
- `frontend/src/features/buddy/_BuddySettingsModel.tsx` — Modell-/Runtime-Konfiguration.
- `frontend/src/features/buddy/_BuddySettingsTools.tsx` — Suche, Kategorien, unbekannte Tools, MCP und Sicherheitsoptionen.
- `frontend/src/features/buddy/_BuddySettingsSkills.tsx` — Skill-Herkunft, Aktivierung und Buddy-Skill-CRUD.
- `frontend/src/features/buddy/_BuddySettingsAdvanced.tsx` — vollständige Compaction-/Cache-Parameter.
- `frontend/src/features/skills/SkillEditor.tsx` — Legacy-Farben entfernen und neutrales Cockpit-Overlay verwenden.
- `frontend/src/features/skills/types.ts` / `api.ts` — Projekt-Scope und `include_disabled`.
- `frontend/src/i18n/locales/{de,en}/buddy.json` — vollständige Beschriftungen und Zustände.

## Implementierungsreihenfolge

### Task 1: Backend-Vertrag und Tests
- [ ] Tests für vollständiges `GET /buddy/config` ergänzen und rot ausführen.
- [ ] Tests für erlaubte vollständige Buddy-Patches sowie verbotene/fremde Felder ergänzen.
- [ ] `BuddyConfigPatch` mit festen Grenzen erweitern.
- [ ] `_config.get_config` und `_config.patch_config` erweitern.
- [ ] Fokussierte Tests grün ausführen.
- [ ] Commit: `feat(buddy): vollständige Einstellungskonfiguration bereitstellen`

### Task 2: Deaktivierte Skills reaktivierbar machen
- [ ] API-Test für Standardfilter und `include_disabled=true` ergänzen und rot ausführen.
- [ ] Query-Parameter implementieren, Standardverhalten unverändert lassen.
- [ ] Frontend-Typ um `project` erweitern.
- [ ] Fokussierte Tests grün ausführen.
- [ ] Commit: `fix(skills): deaktivierte Agent-Skills vollständig auflisten`

### Task 3: Cockpit-Grundgerüst und Modell/Advanced
- [ ] `BuddySettingsPage` auf `CockpitShell`/`CockpitTopbar` und responsive Navigation umstellen.
- [ ] Modell- und Advanced-Panels ergänzen.
- [ ] Draft, Retry, Save-Bar und Fehlerzustände verdrahten.
- [ ] Frontend-Build grün ausführen.
- [ ] Commit: `feat(buddy): vollständiges Einstellungscockpit aufbauen`

### Task 4: Tools, MCP und Sicherheitsoptionen
- [ ] Tool-Katalog mit Suche, Kategorien und Beschreibungen bauen.
- [ ] Unbekannte gespeicherte Tools sichtbar erhalten.
- [ ] MCP-, Langzeitgedächtnis- und Bestätigungsoptionen integrieren.
- [ ] Frontend-Vertragstest beziehungsweise statische Contract-Checks ergänzen.
- [ ] Commit: `feat(buddy): Tools und MCP vollständig konfigurierbar machen`

### Task 5: Skills und moderner Skill-Editor
- [ ] Effektive Skills inklusive deaktivierter laden.
- [ ] Scope-Badges, Suche und Aktivierung ergänzen.
- [ ] Buddy-eigene Skill-Erstellung/-Bearbeitung/-Löschung integrieren.
- [ ] `SkillEditor` vom Legacy-Design lösen.
- [ ] Commit: `feat(buddy): Skills im Einstellungscockpit verwalten`

### Task 6: Verifikation und Abschluss
- [ ] Vollständige Core-Tests und Ruff ausführen.
- [ ] Frontend-Produktionsbuild ausführen.
- [ ] Browser-Smoke auf Desktop und Mobil: alle Tabs, Toolsuche, Skill-Toggle, Save/Reload.
- [ ] Security- und Strukturreview durchführen; Befunde beheben.
- [ ] Code-Graph aktualisieren.
- [ ] PR erstellen und nach grünen Gates mergen.

## Nicht in diesem Plan

- Direkte Bearbeitung des rohen Buddy-System-Prompts oder der Soul-Dateien.
- Umbau des generischen Agenteneditors.
- Administration oder Installation neuer MCP-Server aus den Buddy-Einstellungen.
- Automatische Tool-Freigabe aufgrund von `tools_required` eines Skills.
