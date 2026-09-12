# Projektgebundene Audio-Bibliothek

## Was

Der Musicplayer speichert Tracks nicht länger in einem globalen Modulverzeichnis, sondern pro Projekt im jeweiligen Workspace unter `media/audio/`. Alle Projektmitglieder sehen dieselbe Bibliothek entsprechend ihrer Projektrolle. Tracks können zusätzlich einzeln heruntergeladen werden.

## Warum

Der bisherige Pool unter `data_dir/modules/musicplayer/` überschneidet sich mit dem austauschbaren Modulcode und kann bei Modulupdates gelöscht werden. Zudem fehlt eine Projektgrenze: Metadaten und Dateien sind global statt an den aktiven Arbeitskontext gebunden.

## Speichermodell

- Physischer Pfad: `workspaces/projects/<project_id>/media/audio/<uuid>.mp3`.
- Die DB-Tabelle erhält `project_id`; Listen, Quellen-Deduplizierung und Einzelzugriffe sind immer projektgefiltert.
- Der Browser erhält niemals frei wählbare Dateipfade. Dateinamen bleiben servergenerierte UUID-Namen.
- Vorhandene source-basierte Tracks werden aus `projects/<id>/generated/...` ihrem Projekt zugeordnet und zunächst kopiert, vollständig verifiziert und erst danach aus dem Legacy-Pool entfernt.
- Nicht eindeutig zuordenbare Legacy-Tracks bleiben unzugeordnet und werden keinem Projekt offengelegt.

## Berechtigungen

- Projektrolle `read`: auflisten, streamen und herunterladen.
- Projektrolle `write`: zusätzlich hochladen und generierte Musik aus demselben Projekt importieren.
- Projektrolle `admin`: zusätzlich löschen.
- System-Admins folgen der bestehenden Core-Regel und dürfen alle Projekte verwalten.
- Query-JWTs für Audio-Tags werden gegen den aktuellen Benutzer und dessen aktuelle Projektberechtigung aufgelöst.

## API

Alle Endpunkte liegen unter `/api/modules/musicplayer/projects/{project_id}`:

- `GET /tracks` — Bibliothek plus effektive Schreib-/Löschrechte.
- `POST /tracks` — MP3-Upload für `write`.
- `GET /tracks/{track_id}/stream` — Inline-Stream für `read`, optional `download=1` als Attachment.
- `DELETE /tracks/{track_id}` — Löschen für `admin`.
- `GET /generated` und `POST /generated/import` — nur Quellen aus demselben Projektworkspace, mindestens `write`.

## Frontend

- Der Buddy-Media-Slot verwendet die bereits übergebene aktive `projectId`.
- Ohne aktives Projekt wird keine globale Bibliothek geladen; der Player zeigt einen Hinweis zur Projektauswahl.
- Upload/Import erscheinen nur mit Schreibrecht, Löschen nur mit Projekt-Adminrecht.
- Jede Trackzeile erhält einen Download-Button.
- Ein Projektwechsel setzt die lokale Wiedergabeinstanz zurück.

## Update-Sicherheit

Der Core-Modulvertrag erhält optionale, strikt validierte `persistent_paths`. Beim Ersetzen eines Moduls werden nur deklarierte reguläre Dateien innerhalb des Modulroots zwischengesichert und anschließend konfliktfrei wiederhergestellt. Der Musicplayer deklariert für die einmalige Legacy-Übernahme `*.mp3`; die neue Version migriert diese Dateien in die Projektworkspaces.

## Akzeptanzkriterien

- Zwei aufeinanderfolgende Musicplayer-Updates verlieren keine Audiodatei.
- Alle vorhandenen eindeutig zuordenbaren Tracks liegen nach der Migration im richtigen Projektworkspace.
- Projektfremde und nicht angemeldete Nutzer erhalten keinen Zugriff.
- `read`, `write` und `admin` verhalten sich wie definiert.
- Stream, Seekderivat, Download, Upload, Import und Löschen sind projektgebunden getestet.
- Bestehende Trackdateien werden vor dem Entfernen des Legacy-Pools byteweise beziehungsweise per Größe verifiziert.
