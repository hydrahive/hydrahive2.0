# Spec: Wiederkehrende Agentenaufgaben und Heartbeat-Verwaltung

## Ziel

HydraHive erhält eine persistente Verwaltung für wiederkehrende Aufgaben. Eine Aufgabe kann direkt einen Projekt-Agenten oder den Buddy mit einem gespeicherten Auftrag ausführen. Optional kann sie stattdessen ein Butler-Event auslösen. Die Verwaltung ist in der Administration sichtbar und in Agenten-, Buddy- und Projekt-Einstellungen erreichbar.

Der technische Compute-Node-Heartbeat bleibt davon getrennt: Er überwacht die Erreichbarkeit eines Nodes und startet keine Benutzeraufgaben.

## Bestehende Bausteine

- `compute/channel.py` und `compute/channel_monitor.py`: technischer Node-Heartbeat, nicht wiederverwenden als Aufgabenscheduler.
- `butler/scheduler.py`: Cron-Emitter im Minutentakt; kann als optionaler Event-Zielpfad dienen, ist für 10-Sekunden-Aufgaben allein aber nicht ausreichend.
- `modules/jobs.py`: statische Modul-Jobs; nicht für benutzerdefinierte, persistente Zeitpläne verwenden.
- Agenten-Runner/API: für direkte Ausführung wiederverwenden, damit Projekt-, Workspace-, Tool- und Berechtigungskontext identisch zu normalen Agentenläufen bleibt.
- Vorhandener Frontend-Trigger `heartbeat_fired`: als kompatibler Alias erhalten, aber durch das neue Scheduling-Event wieder verkabeln.

## Datenmodell

Neue persistente Tabelle `scheduled_agent_tasks`:

- `task_id` — UUID/UUID7
- `owner` — Benutzer-ID
- `scope` — `user` oder `project`
- `project_id` — optional, bei Projektaufgaben verpflichtend
- `target_type` — `agent` oder `buddy`
- `target_id` — Agent-ID beziehungsweise Buddy-ID
- `title` — kurze Bezeichnung
- `prompt` — auszuführender Auftrag
- `execution_mode` — `direct` (Standard) oder `butler_event`
- `interval_seconds` — ganzzahlig, mindestens 10
- `enabled`
- `overlap_policy` — zunächst `skip` (kein paralleler Lauf desselben Tasks)
- `next_run_at`
- `last_run_at`
- `last_status` — `never`, `running`, `succeeded`, `failed`, `skipped`
- `last_error`
- `failure_count`
- `created_at`, `updated_at`

Neue Tabelle `scheduled_agent_task_runs`:

- `run_id`, `task_id`
- `started_at`, `finished_at`
- `status`
- `execution_id`/`session_id` sofern vorhanden
- `error`
- begrenzte Ergebnis-/Trace-Metadaten, kein unbeschränktes Prompt-/Output-Archiv in der Scheduler-Tabelle

## Ausführungsregeln

1. Der Scheduler läuft als überwachte Core-Hintergrundaufgabe.
2. Er prüft mindestens jede Sekunde beziehungsweise in einem kurzen, konfigurierten Takt fällige Aufgaben.
3. Eine Aufgabe wird nur mit Datenbank-Lease/atomarem Statuswechsel übernommen, damit sie bei konkurrierenden Backend-Prozessen nicht doppelt startet.
4. `overlap_policy=skip` verhindert, dass ein 10-Sekunden-Intervall neue LLM-Läufe stapelt, solange der vorherige Lauf aktiv ist.
5. Fehler werden pro Aufgabe isoliert, geloggt und in `last_error`/`failure_count` gespeichert.
6. Wiederholte Fehler lösen einen begrenzten Backoff aus; die Aufgabe wird nicht ohne explizite Aktion dauerhaft gelöscht.
7. Ein Lauf kann manuell gestartet, pausiert, fortgesetzt und abgebrochen werden.
8. Direkte Ausführung nutzt den bestehenden Agenten-/Buddy-Runner mit dem Projekt- und Workspace-Kontext des Ziels.
9. Im Modus `butler_event` wird ein standardisiertes `schedule_fired`-Event emittiert. `heartbeat_fired` bleibt als Rückwärtskompatibilitätsname für vorhandene Butler-Flows erhalten.
10. Verpasste Läufe nach einem Backend-Neustart werden standardmäßig nicht nachgeholt; der nächste Lauf wird ab `now` geplant.

## Sicherheits- und Lastgrenzen

- Mindestintervall: 10 Sekunden.
- UI-Warnung für Intervalle unter 60 Sekunden.
- Maximalzahl aktiver Zeitpläne pro Benutzer/Projekt über Settings begrenzbar.
- Maximale parallele direkte Läufe pro Benutzer und global.
- Default-Timeout je Lauf.
- Prompt- und Titel-Längen werden serverseitig begrenzt.
- Authentifizierung und Scope-Prüfung bei jeder CRUD- und Run-Aktion.
- Butler-Event-Ausführung darf nicht zu einer zweiten direkten Ausführung desselben Zeitplans führen.

## API

Vorgesehene API unter `/api/scheduled-tasks`:

- `GET /api/scheduled-tasks?project_id=...`
- `POST /api/scheduled-tasks`
- `GET /api/scheduled-tasks/{task_id}`
- `PATCH /api/scheduled-tasks/{task_id}`
- `DELETE /api/scheduled-tasks/{task_id}`
- `POST /api/scheduled-tasks/{task_id}/run`
- `POST /api/scheduled-tasks/{task_id}/pause`
- `POST /api/scheduled-tasks/{task_id}/resume`
- `GET /api/scheduled-tasks/{task_id}/runs`

Admin darf alle Zeitpläne sehen und verwalten. Normale Benutzer sehen nur eigene beziehungsweise projektbezogene Zeitpläne, auf die sie Zugriff haben.

## Frontend

### Administration

Neuer Bereich `Admin → Automationen` mit:

- Liste/Filter nach Status, Projekt, Ziel und Ausführungsmodus
- Intervall, letzter/nächster Lauf und Fehlerstatus
- Pause/Fortsetzen, Jetzt ausführen, Löschen
- globale Schutz-/Scheduler-Einstellungen für Administratoren

### Agenten-Einstellungen

Neue Registerkarte `Wiederkehrende Aufgaben` im Agenten-Editor. Ziel-Agent ist vorausgewählt; Aufgabe kann dort angelegt und bearbeitet werden.

### Buddy-Einstellungen

Neue Registerkarte `Intervallaufgaben`. Ziel ist der aktuelle Benutzer-Buddy.

### Projekt-Cockpit

Projektbezogene Aufgaben werden im Agenten-Editor und in einem Projekt-Panel angezeigt. Bei Erstellung wird das aktive Projekt automatisch gebunden.

### Butler

Der bestehende `heartbeat_fired`-Trigger bleibt in der Palette, ist nicht mehr als `UNWIRED_TRIGGER` markiert und erhält den Ausführungsmodus `butler_event` als wählbare Option bei einer geplanten Aufgabe.

## Implementierungsreihenfolge

1. Datenbankmigration, Repository und Pydantic-Modelle; Tests für Grenzen, Scope und Zeitplanstatus.
2. Scheduler-Service mit atomarem Claim, Skip-overlap, Fehlerstatus und Shutdown-Verhalten; Tests mit kurzer Testzeit und kontrollierter Uhr.
3. Direkte Agent-/Buddy-Ausführung über bestehende Runner-APIs; Auth- und Projektkontext testen.
4. Optionaler Butler-Event-Adapter sowie kompatibler `heartbeat_fired`-Trigger.
5. CRUD-/Run-/Pause-/Resume-API mit Auth- und Projektprüfungen.
6. Gemeinsame Frontend-Komponenten für Liste, Editor und Status.
7. Einbindung in Administration, Agenten-Einstellungen, Buddy-Einstellungen und Projekt-Cockpit.
8. Hilfe-/i18n-Dokumentation, Migrationstest, Backend-/Frontend-Test und HydraHive-Code-Review.

## Akzeptanzkriterien

- [ ] Ein Benutzer kann eine Aufgabe für einen Agenten oder Buddy mit einem Intervall ab 10 Sekunden anlegen.
- [ ] Direkter Agent-/Buddy-Lauf ist der Standard.
- [ ] `butler_event` ist als alternative Ausführungsart auswählbar.
- [ ] Ein laufender Task wird standardmäßig nicht parallel erneut gestartet.
- [ ] Aufgaben bleiben nach Backend-Neustart erhalten und werden korrekt weitergeplant.
- [ ] Admin sieht alle Zeitpläne und kann sie pausieren, ausführen oder löschen.
- [ ] Agenten-, Buddy- und Projekt-Einstellungen zeigen die jeweils zulässigen Aufgaben.
- [ ] Letzter Lauf, nächster Lauf, Status und Fehler sind sichtbar.
- [ ] Der technische Compute-Heartbeat bleibt unverändert und getrennt.
- [ ] Vorhandene Tasks, Butler-Flows und normale Agentenläufe bleiben kompatibel.

## Nicht in diesem Plan

- Kein Ersatz des technischen Compute-Node-Heartbeats.
- Keine freie Cron-Syntax in der ersten Version; zunächst feste Intervalle.
- Keine parallele Ausführung desselben Tasks als Standard.
- Keine unbeschränkte Speicherung kompletter LLM-Verläufe in der Scheduler-Datenbank.
