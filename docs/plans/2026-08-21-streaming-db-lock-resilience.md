# Plan: Streaming-Downloader gegen DB-Locks härten

## Ziel

Streaming-Downloads und Abbrüche blockieren bei kurzzeitiger SQLite-Konkurrenz nicht mehr den FastAPI-Event-Loop. Fortschrittsschreibvorgänge werden begrenzt und dürfen bei einem Lock ausfallen, während Zustandswechsel mit kurzen Retries gespeichert werden. Ein Abbruch beendet und reapet den laufenden yt-dlp-Prozess zuverlässig.

## Dateien

- `core/src/hydrahive/db/connection.py` — optionales SQLite-Connection-Timeout ermöglichen.
- `core/src/hydrahive/db/streaming.py` — Timeout für Statusupdates durchreichen.
- `core/src/hydrahive/streaming/downloader.py` — DB-I/O auslagern, Fortschritt drosseln, Subprozess-Lebenszyklus absichern.
- `core/src/hydrahive/api/routes/streaming.py` — DB-Aufrufe im Async-Endpoint auslagern und Cancel asynchron ausführen.
- `core/tests/test_streaming_downloader.py` — Lock-, Fortschritts- und Prozess-Cancel-Verhalten testen.

## Implementierungsreihenfolge

### Task 1: Nicht blockierende Statusupdates
- [ ] Tests für best-effort Fortschrittsupdates bei `database is locked` und Retries kritischer Updates schreiben.
- [ ] Tests rot ausführen.
- [ ] DB-Timeout parametrierbar machen und Downloader-DB-Aufrufe via `asyncio.to_thread` auslagern.
- [ ] Fortschritt nur bei geändertem Prozentwert schreiben und Locks bei Fortschritt protokolliert überspringen.
- [ ] Tests grün ausführen.

### Task 2: Sauberer Download-Abbruch
- [ ] Tests schreiben, dass Cancel den Prozess beendet, wartet und Status `Abgebrochen` setzt.
- [ ] Tests rot ausführen.
- [ ] Laufende Prozesse je Job registrieren; Cancel beendet den Prozess statt den gemeinsamen Queue-Task.
- [ ] Bei Coroutine-Cancellation/Timeout Prozess terminieren und reapen; Part-Datei aufräumen.
- [ ] Tests grün ausführen.

### Task 3: Route und Regression
- [ ] Async-Routen-Aufrufe auf Thread-Offloading/async Cancel umstellen.
- [ ] Downloader-Tests, relevante API-Tests und Ruff ausführen.
- [ ] HH-Architekturreview und vollständige Abschlussverifikation ausführen.
- [ ] Commit, Push, PR und Deployment gemäß bestehendem Workflow.

## Akzeptanzkriterien

- [ ] Ein gesperrtes SQLite bei einem Fortschrittsupdate friert den Event-Loop nicht ein und beendet den Download nicht.
- [ ] Kritische Zustandswechsel werden kurz wiederholt und Fehler danach sichtbar weitergereicht.
- [ ] Identische Fortschrittsprozente erzeugen keine wiederholten Commits.
- [ ] Cancel liefert keinen 500er wegen eines synchron im Event-Loop wartenden DB-Aufrufs.
- [ ] Cancel und Timeout lassen keinen yt-dlp-Prozess zurück.
- [ ] Bestehende Streaming-/API-Funktionalität bleibt grün.

## Nicht in diesem Plan

- Umstellung der gesamten HydraHive-Datenbank von SQLite auf PostgreSQL.
- Änderung der maximalen parallelen Downloadanzahl.
- Automatisches Aufräumen fremder Programme in `/tmp`; der konkrete MC-Tempstau wurde operativ behoben.
