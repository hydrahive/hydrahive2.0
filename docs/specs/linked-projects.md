# Verknüpfte Projekte: Projekt-Agent und Spezialisten lesen weitere Projekte

Stand 10.10.2026 · Task 12f3b7fd · Till: „Projekt-Agenten sollen Zugriff auf die Projekte haben, die sie brauchen, und
ich will das einstellen können.“ Anlass: der HydraVR-Agent braucht viel Wissen aus HydraHive DEV.
Entscheidungen Till 10.10.: **nur lesen** (Schreiben per Task an den dortigen Agenten), **auch für Spezialisten** des
Projekts, **nur wenn der Nutzer des Laufs selbst Mitglied** des verknüpften Projekts ist.

## Einstellung
Feld am Projekt: `linked_projects: [<projekt-id>, …]` (max. 20). Ändern über `PUT /api/projects/{id}/linked-projects`
`{"projects": [...]}` – erlaubt nur, wer im eigenen Projekt Admin ist UND in jedem verknüpften Projekt mindestens
`write` hat (System-Admin immer). Sonst könnte sich jemand fremde Projekte in seinen Agenten holen. Unbekannte
Projekte, das Projekt selbst, Doppelte → 400. Jede Änderung → Projekt-Audit (`linked_projects_changed`).
Oberfläche: Projekt-Cockpit → Einstellungen → „Verknüpfte Projekte (nur lesen)“.

## Wirkung in einem Lauf
Gilt für Läufe von Agenten, die zum Projekt gehören: Projekt-Agent (`project.agent_id`) und Spezialisten mit
`project_id` = Projekt. Wirksam ist ein verknüpftes Projekt nur, wenn der **Nutzer des Laufs** (Sitzungs-Nutzer; bei
Aufträgen per ask_agent der Besitzer des Spezialisten) dort mindestens `read` hat.

1. **Dateien lesen:** `safe_path` erlaubt zusätzlich Ziele in den Workspaces der wirksam verknüpften Projekte – nur für
   lesende Werkzeuge (`file_read`, Datei-Such-Plugins `grep`/`find`/`tree`). `file_write`/`file_patch` bleiben im
   eigenen Workspace. Pfade: absolut (`/var/lib/hydrahive2/workspaces/projects/<id>/…`) oder über den Ordner
   `linked/<Name>` im eigenen Workspace (Symlink, wird bei Änderung der Liste neu gesetzt, wie beim Master).
2. **Wissen:** wirksam verknüpfte Projekte zählen zu den Datamining-Projekten des Laufs (zusätzlich zu
   `knowledge_access.projects`).
3. **Hinweis im System-Prompt:** „Verknüpfte Projekte (nur lesen): Name → Pfad“ – damit der Agent sie findet.

## Nicht in dieser Etappe
Tasks der verknüpften Projekte lesen, Code-Graph der verknüpften Projekte, Schreiben (bewusst: per Task an den
dortigen Agenten), shell_exec-Isolation (eigener Task 3bd963b2 – Shell läuft weiterhin als Dienst-Nutzer).

## Akzeptanz
- Verknüpfen nur mit Rechten in beiden Projekten; Audit-Eintrag.
- Projekt-Agent und Projekt-Spezialist lesen Datei aus verknüpftem Projekt; schreiben dort → abgelehnt.
- Nutzer ohne Mitgliedschaft im verknüpften Projekt → Lesen abgelehnt, Wissen nicht sichtbar.
- Agent eines anderen Projekts / Master: unverändert.
- Echter Test auf hydratest mit echtem Lauf (Werkzeug-Ebene) und zwei Nutzern.
