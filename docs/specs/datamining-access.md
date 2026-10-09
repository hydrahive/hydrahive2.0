# Datamining-Zugriff je Agent (E0)

Stand 09.10.2026 · Task b17f9e38 (Wissensräume, Etappe E0) · freigegeben von Till am 09.10.

## 1. Problem
Die Datamining-Werkzeuge (`datamining_search`, `datamining_semantic`, `datamining_timeline`,
`datamining_today`) filtern nur nach dem Nutzer des Laufs (`ToolContext.user_id`). Jeder Agent eines
Nutzers kann damit dessen gesamtes Langzeitgedächtnis durchsuchen – projektübergreifend, auch Sitzungen
anderer Agenten (Filter `agent_name` frei wählbar).

Gemessen am 09.10. (Datamining .2): 544.685 Ereignisse, 49 % mit Projekt-ID. Gesundheitsabfragen
(`query_fhir_data`, `query_health_data`) liegen im Projekt „Arztpraxis“ (18), im DEV-Projekt (15, Buddy
war dort aktiv) und ohne Projekt bei admin's Buddy (16). Ein reiner Projektfilter reicht deshalb nicht.

## 2. Regel
Jeder Agent hat eine Einstellung **`knowledge_access`** (nur Admin darf sie ändern):

```json
{"scope": "project" | "user", "projects": ["<projekt-id>", ...], "sensitive": false}
```

- **`scope: "project"`** (Standard für Projekt-Agenten und Spezialisten): nur Ereignisse mit
  `project_id` = Projekt des Laufs **oder** einem Projekt aus `projects`. Ohne Projekt im Lauf und ohne
  `projects` → keine Treffer (nicht: alles).
- **`scope: "user"`** (Standard für Master-Agenten/Buddys): alles des eigenen Nutzers, wie bisher.
- **Immer**: nur Ereignisse des eigenen Nutzers (`username`). Unverändert.
- **Sensible Sitzungen**: Hat eine Sitzung ein sensibles Werkzeug benutzt (heute: `query_fhir_data`,
  `query_health_data`), sind ALLE Ereignisse dieser Sitzung unsichtbar – außer `sensitive: true`.
  Standard: `true` für Master-Agenten/Buddys, `false` für alle anderen.
- Fehlt die Einstellung, gilt der Standard nach Agent-Typ. Bestehende Agenten müssen nicht migriert werden.

Der Filter `agent_name` bleibt erlaubt, wirkt aber nur innerhalb der erlaubten Menge.

## 3. Umsetzung
- `db/_mirror_scope.py`: baut aus `(agent, project_id, username)` einen SQL-Filter (nur Parameter, kein
  String-Einbau von Werten); wird in `_text_search`, `_semantic_search`, `list_sessions` eingesetzt.
- Sensible Sitzung: `NOT EXISTS (SELECT 1 FROM events s WHERE s.session_id = events.session_id AND
  s.tool_name = ANY($n))` – nutzt den vorhandenen Index `events_tool` + `events_session`.
- `agents`: Feld `knowledge_access` mit Validierung (scope-Wert, Projekt-IDs existieren, bool). Änderbar über
  die Admin-Route `PATCH /api/agents/{id}`. NICHT über `configure_specialist`/`create_specialist`
  (Projekt-Agenten dürfen sich/ihren Spezialisten keinen Zugriff geben).
- Oberfläche: folgt (E2). Bis dahin per API/Admin.

## 4. Nicht in E0
Wissensräume mit Gruppen (Familie), Schutzstufen als Spalte, Kristalle, Karten-Recall. Karten im
System-Prompt (`top_cards_for`) sind schon auf den eigenen Agenten begrenzt.

## 5. Akzeptanz
- Projekt-Agent findet Ereignisse seines Projekts, nicht die eines anderen Projekts, nicht die ohne Projekt.
- Mit `projects: [X]` zusätzlich Projekt X.
- `scope: user` findet alles des Nutzers, nie Ereignisse anderer Nutzer.
- Sitzung mit `query_health_data` ist für Projekt-Agenten unsichtbar, auch im eigenen Projekt; für Buddys sichtbar.
- Werte landen nie per String im SQL (Test mit bösartiger Projekt-ID).
- Live auf .2: DEV-Projekt-Agent findet „query_health_data“ nicht mehr; Buddy schon.
