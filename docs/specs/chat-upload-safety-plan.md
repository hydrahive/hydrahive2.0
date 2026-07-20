# Plan: Sicherer Chat-Dateiupload bis 100 MiB

## Ziel

Chat-Anhänge bis 100 MiB pro Datei und 200 MiB pro Nachricht werden sichtbar validiert, serverseitig begrenzt, speicherschonend gestreamt und im richtigen Session-Workspace abgelegt.

## Dateien

- `core/src/hydrahive/api/routes/_files.py` — gemeinsame Uploadgrenzen, Größenvalidierung und Chunk-Streaming
- `core/src/hydrahive/api/routes/_session_msg_helpers.py` — Session-Workspace, Batch-Cleanup und HTTP-Fehlerabbildung
- `core/src/hydrahive/api/middleware/upload_limit.py` — 205-MiB-Hard-Limit vor Multipart-Parsing
- `core/src/hydrahive/api/main.py` — Request-Limit-Middleware registrieren
- `core/src/hydrahive/api/routes/sessions_messages.py` — vollständige Session übergeben und Resend-Reihenfolge absichern
- `core/tests/test_chat_uploads.py` — Bild/Text-Kompatibilität, Binär-Streaming, Limits, Cleanup, Path Traversal und Projekt-Workspace
- `frontend/src/features/chat/MessageInput.tsx` — 100-/200-MiB-Validierung und sichtbarer Fehlerzustand
- `frontend/src/features/chat/api.ts` — strukturierte Backendfehler lokalisiert anzeigen
- `frontend/src/shared/api-client.ts` — gemeinsamen API-Error-Formatter wiederverwenden
- `frontend/src/i18n/locales/{de,en}/chat.json` — lokale Auswahlfehler
- `frontend/src/i18n/locales/{de,en}/errors.json` — serverseitige Uploadfehler
- `installer/modules/60-nginx.sh` — 205-MiB-Grenze vor dem Multipart-Parser
- `installer/modules-mac/60-nginx.sh` — dieselbe Grenze für macOS
- `installer/update.sh` — bestehende Installationen zum Nginx-Rewrite markieren
- `docs/specs/chat-upload-safety.md` — verbindliches Verhalten

## Implementierungsreihenfolge

### Task 1: Backend-Limits und Streaming

- [ ] Tests in `core/tests/test_chat_uploads.py` schreiben:
  - Binärdatei innerhalb des Limits wird vollständig gespeichert
  - Datei über 100 MiB wird abgelehnt
  - Nachricht über 200 MiB wird abgelehnt
  - Teil-Datei wird nach Größenfehler entfernt
  - Path-Traversal-Dateiname wird abgelehnt
- [ ] Tests ausführen und RED bestätigen
- [ ] Konstanten für 100 MiB pro Datei und 200 MiB gesamt ergänzen
- [ ] Größenprüfung vor Verarbeitung implementieren
- [ ] Binärdateien über temporäre Datei in 1-MiB-Chunks schreiben und atomar umbenennen
- [ ] Pro Request einen eindeutigen `.hydrahive/uploads/`-Batch anlegen
- [ ] Basis-Dateinamen erzwingen, Kollisionen eindeutig umbenennen und Projektdateien nie überschreiben
- [ ] Bei jedem Fehler den vollständigen Batch entfernen
- [ ] Chat-Message-Requests in Nginx vor dem Multipart-Parser auf 205 MiB begrenzen
- [ ] Tests ausführen und GREEN bestätigen

### Task 2: Session-Workspace korrekt auflösen

- [ ] Tests ergänzen:
  - Projekt-Session verwendet Projekt-Workspace
  - projektlose Session verwendet Agent-Workspace
- [ ] Tests RED ausführen
- [ ] `build_user_content` auf Session-Kontext umstellen und bestehende Aufrufer anpassen
- [ ] Vorhandene `resolve_run_context`-Logik wiederverwenden, damit Runner und Upload dieselbe Workspace-Entscheidung treffen
- [ ] Tests GREEN ausführen

### Task 3: Frontend-Validierung und Rückmeldung

- [ ] Explizite Konstanten für 5 Dateien, 100 MiB pro Datei und 200 MiB insgesamt verwenden
- [ ] Einzeldatei-, Gesamt- und Anzahlfehler unterscheiden
- [ ] Fehlertext im `MessageInput` sichtbar rendern
- [ ] deutsche und englische Übersetzungen ergänzen
- [ ] Sicherstellen, dass APK/EXE nicht per `accept` gefiltert werden
- [ ] TypeScript-Build und ESLint ausführen

### Task 4: Gesamtverifikation

- [ ] Relevante Backend-Tests ausführen
- [ ] vollständigen Frontend-Produktionsbuild ausführen
- [ ] `git diff --check` und HH-Review durchführen
- [ ] Security-Review: serverseitige Limits, Path Traversal, temporäres Cleanup, keine Ausführung
- [ ] Commit und Push
- [ ] Produktionsupdate durchführen
- [ ] echten Upload einer Datei knapp über der alten Grenze verifizieren
- [ ] Code-Graph aktualisieren

## Akzeptanzkriterien

- [ ] 54-MB-APK kann angehängt und im aktiven Projekt gefunden werden
- [ ] >100-MiB-Datei hat sichtbaren Frontendfehler und HTTP-413-Backendschutz
- [ ] >200-MiB-Gesamtauswahl wird abgelehnt
- [ ] keine vollständige Binärdatei wird in den RAM geladen
- [ ] keine Teil-Datei nach Abbruch oder Limitfehler
- [ ] kein Pfad verlässt den Workspace
- [ ] Bild-/Textupload regressionsfrei

## Nicht in diesem Plan

- Virenscan oder Sandboxing der hochgeladenen Datei
- automatische Ausführung
- Upload-Fortschrittsbalken
- Änderung der spezialisierten VM-/ISO-Uploadwege
