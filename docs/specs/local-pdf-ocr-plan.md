# Plan: Lokales Lesen von Text- und Scan-PDFs

## Ziel

HydraHive-Agenten können PDFs auf Host-Projekten mit einem sicheren lokalen `read_document`-Werkzeug lesen. Textseiten nutzen Poppler, Scan-Seiten Tesseract. Installer und Updatepfade rüsten die Laufzeitprogramme auf macOS und Ubuntu/Debian automatisch nach.

## Dateien

- `core/src/hydrahive/tools/read_document.py` — Tool-Vertrag, Pfad-/Eingabeprüfung und Ergebnisformat.
- `core/src/hydrahive/tools/_document_local.py` — begrenzte lokale Poppler-/Tesseract-Ausführung.
- `core/src/hydrahive/tools/__init__.py` — Tool registrieren.
- `core/src/hydrahive/agents/_defaults.py` — Standardwerkzeug für Master/Projekt.
- `core/src/hydrahive/runner/_project_tool_scope.py` — absichern, dass Container es nicht erhalten (Negativtest; Allowlist bleibt geschlossen).
- `core/tests/test_read_document.py` — Werkzeug-, Sicherheits- und Fehlerfälle.
- `core/tests/test_agent_defaults.py` bzw. bestehender passender Test — Default-/Container-Scope.
- `installer/lib/mac-document-tools.sh` — Homebrew-Nachrüstung über Rollenmodell.
- `installer/modules-mac/00-deps.sh` — Erstinstallation ruft Dokument-Abhängigkeiten auf.
- `installer/update-mac.sh` — bestehende Macs nach `git pull` nachrüsten.
- `installer/lib/debian-document-tools.sh` — idempotente apt-Nachrüstung.
- `installer/modules/00-deps.sh` — Linux-Erstinstallation.
- `installer/update.sh` — bestehende Linux-Instanzen nachrüsten.
- `core/tests/test_mac_document_tools.py` — Intel/ARM, Brew-Rolle und Update-Verkabelung.
- `core/tests/test_document_tools_installer.py` — Debian-Erst-/Updatepfad.
- `core/src/hydrahive/skills/system_defaults/document-reading.md` — knappe Nutzungsregeln für PDFs und OCR.

## Implementierungsreihenfolge

### Task 1: Werkzeugvertrag und Grenzen

- [ ] Tests für Schema, Pfadauflösung, PDF-Kennung, Dateigröße, Seitenparameter und OCR-Sprachen schreiben.
- [ ] Tests rot ausführen.
- [ ] `read_document.py` mit Validierung und klaren Fehlern implementieren.
- [ ] Tests grün ausführen und committen.

### Task 2: Text-PDF und OCR-Fallback

- [ ] Fake-Prozess-Tests für pdfinfo, pdftotext, gemischte Seiten, OCR, Timeout, fehlende Programme, minimales Environment und Ausgabegrenze schreiben.
- [ ] Tests rot ausführen.
- [ ] `_document_local.py` mit argv-Subprozessen, Prozessgruppenabbruch, Tempdir und Seitenlogik implementieren.
- [ ] Tests grün ausführen und committen.

### Task 3: Registrierung und Agenten-Defaults

- [ ] Tests schreiben: Registry enthält `read_document`; Master/Projekt bekommen es; Container-Allowlist enthält es nicht.
- [ ] Tests rot ausführen.
- [ ] Imports, Registry und Defaults ergänzen; Container-Allowlist unverändert lassen.
- [ ] Tests grün ausführen und committen.

### Task 4: macOS-Abhängigkeiten

- [ ] Skripttests für fehlende/vorhandene Programme, `as_brew`, ARM/Intel und Verkabelung in Neuinstallation/Update schreiben.
- [ ] Tests rot ausführen.
- [ ] `mac-document-tools.sh`, Erstinstallation und Updatepfad implementieren.
- [ ] Tests grün ausführen und committen.

### Task 5: Ubuntu-/Debian-Abhängigkeiten

- [ ] Skripttests für idempotente apt-Installation und Verkabelung schreiben.
- [ ] Tests rot ausführen.
- [ ] Debian-Hilfsskript, 00-deps und update.sh ergänzen.
- [ ] Tests grün ausführen und committen.

### Task 6: Anleitung und echte lokale Probe

- [ ] Skill-/Doku-Test für den Hinweis „PDF nicht mit file_read“ schreiben.
- [ ] System-Skill ergänzen.
- [ ] Lokale Text-PDF und Scan-PDF ausschließlich aus generierten Testdaten erzeugen und lesen.
- [ ] Keine Kundendokumente kopieren oder verwenden.
- [ ] Committen.

### Task 7: Gesamtprüfung

- [ ] Fokustests und Mutanten ausführen.
- [ ] Vollständige Core-Suite und Ruff ausführen.
- [ ] Security-Audit, `hh-review` und `labor-review` durchführen.
- [ ] Test auf Intel-Test-Mac nach ausdrücklicher Betriebsfreigabe bzw. als PR-Abnahme vormerken.
- [ ] PR erstellen und CI prüfen.

## Akzeptanzkriterien

- [ ] Alle Kriterien aus `local-pdf-ocr.md` sind durch Tests oder dokumentierte Plattformabnahme belegt.
- [ ] Keine Secrets in Kindprozessen und keine Pfade außerhalb des Workspace.
- [ ] Bestehende Macs und Linux-Instanzen werden über den normalen Updateweg nachgerüstet.
- [ ] Der Updateweg bleibt bei bereits installierten Programmen schnell und idempotent.
- [ ] Tool und Produktionsdateien bleiben unter etwa 200 Zeilen pro Datei.

## Nicht in diesem Plan

- PDF-Manipulation oder `.txt`-Sidecars.
- Cloud-OCR.
- Projektcontainer-Paketmanagement.
- Reparatur des separat gemeldeten Frontendfehlers ohne dessen Updateprotokoll.
