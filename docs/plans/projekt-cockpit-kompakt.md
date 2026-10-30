# Plan: Projekt-Cockpit kompakter

Task `36bd2884`, Folgeschritt nach #666 (Admin-Startseite). Till am 30.10.2026: „mache es der reihe nach, und mache was am besten ist“.

## Befund (hydratest, Projekt mit 15 Agenten im Team, 1440×900)
- Linke Spalte: „Projekt-Agenten & Spezialisten“ ist **875 px** hoch (15 Agenten je 2 Zeilen: Name+Rolle, Modell).
  Git Status, KI Einstellungen und Verbrauch rutschen unter den Rand, die Spalte scrollt.
- Rechte Spalte: feste Aufteilung 32 % Git / 38 % Workspace / 30 % Tasks. Vom Workspace bleiben nach Kopf, Suche und
  „Ordner hoch“ nur **~156 px** für die Dateiliste (5 Zeilen). Leere Tasks bekommen trotzdem 30 %.

## Ziel
1. **Team-Liste kompakt:**
   - eine Zeile je Agent (Name, kleines Rollen-Schild, Modell nur als Tooltip und beim Lead bzw. gewählten Agenten)
   - Es werden der Lead, der gewählte Agent und weitere bis **5 Agenten** gezeigt, dazu der Knopf „Alle 15 anzeigen“ bzw. „Weniger“.
   - Ab 8 Agenten erscheint eine Suchzeile (filtert Name und Modell).
2. **Rechte Spalte:** Der Workspace bekommt den meisten Platz.
   - neue Aufteilung **28 % Git / 50 % Workspace / 22 % Tasks**
   - Tasks bleiben scrollbar
   - Der Workspace-Kopf wird kompakter: Etikett und Titel in einer Zeile, Suche und Knöpfe in einer Zeile.

## Dateien
- `frontend/src/features/cockpit/project/agentTeam.ts` + Test (neu): `teamList(agents, leadId, specialistIds)`,
  `visibleTeam(team, { selectedId, expanded, query, limit })` → `{ shown, hidden }`
- `frontend/src/features/cockpit/project/ProjectAgentsPanel.tsx`: einzeilig, „Alle anzeigen“, Suche ab 8
- `frontend/src/features/cockpit/ProjectCockpitPage.tsx`: `xl:grid-rows-[28fr_50fr_22fr]`
- `frontend/src/features/cockpit/project/ProjectWorkspacePanel.tsx`: Kopf kompakter

## Reihenfolge
1. `agentTeam.test.ts` (ROT):
   - Reihenfolge Lead zuerst, Doppelte raus, unbekannte IDs raus
   - eingeklappt: höchstens 5, der **gewählte Agent ist immer dabei**, auch wenn er Nr. 12 ist
   - `hidden` = Rest; aufgeklappt alle; Suche über Name/Modell, ohne Rücksicht auf Groß/Klein
2. Umsetzen (GRÜN), Mutanten: gewählter fällt raus, Limit wirkungslos
3. Panel + Spalte umbauen
4. vitest, tsc, eslint, build; Browser hydratest 1440/1920/390: linke Spalte ohne Scrollen bei 1440 (alle Kästen sichtbar),
   Dateiliste deutlich größer (gemessen), Auswahl eines verborgenen Agenten funktioniert

## Nicht in diesem Plan
Chat-Mitte, Aufbau der Projekt-Box oben links, Module.
