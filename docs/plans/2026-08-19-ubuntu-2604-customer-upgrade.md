# Plan: Kundenfähiges Upgrade Ubuntu 24.04 → 26.04

## Ziel

Ein bestehender HydraHive-Server kann nach dem Ubuntu-Release-Upgrade mit dem
normalen `installer/update.sh` selbstheilend aktualisiert werden, auch wenn das
alte Python 3.12 samt `python3.12-venv` entfernt wurde. PostgreSQL wird über
einen separaten, gesicherten und expliziten Schritt von 16 auf 18 migriert.
Voice-Incus-Container starten nach einem Host-Reboot automatisch. Der Ablauf
ist auf einem echten 24.04→26.04-Testsystem mit erhaltenen Daten verifiziert.

## Dateien

### hydrahive2

- `installer/lib/python-venv.sh` — sichere Interpreter-Auswahl, Zustandsprüfung
  und idempotenter Venv-Rebuild.
- `installer/modules/30-python.sh` — verwendet dieselbe Venv-Logik bei
  Neuinstallation und erneutem Installerlauf.
- `installer/update.sh` — repariert das Venv vor jedem Pip-Aufruf und verwendet
  `python -m pip` statt potenziell veralteter Pip-Shebangs.
- `installer/migrate-postgresql-cluster.sh` — explizite PG16→18-Migration mit
  Preflight, logischem Backup, Erweiterungsprüfung, Port-/Cluster-Guardrails,
  Verifikation und ohne automatisches Löschen des alten Clusters.
- `installer/modules/55-voice.sh` — setzt `boot.autostart=true` für beide
  verwalteten Voice-Container.
- `core/tests/test_python_venv_installer.py` — Verhaltenstests der Venv-Logik.
- `core/tests/test_postgresql_upgrade_script.py` — statische Guardrail-Tests für
  Backup, Zielerweiterung, Migration und Nicht-Löschen des alten Clusters.
- `core/tests/test_voice_installer.py` — Autostart-Regressionsprüfung.
- `docs/ubuntu-2604-upgrade-runbook.md` — kundenfähiger Ablauf mit Backup,
  Kommandos, erwarteten Unterbrechungen, Verifikation und Rollback.

### hydralink

- `installer/modules/20-agentlink.sh` — stoppt `agentlink.service`, bevor ein
  inkompatibles/defektes Venv mit `--clear` aufgebaut wird.
- zugehöriger Installer-Test — verhindert Restart-Races regressiv.

## Implementierungsreihenfolge

### Task 1: Venv-Self-Heal

- [ ] Verhaltenstests für Interpreter-Priorität, expliziten Interpreter,
  gesundes Venv, dangling `python3.12` und Versionswechsel schreiben.
- [ ] Tests rot ausführen.
- [ ] `installer/lib/python-venv.sh` implementieren.
- [ ] `30-python.sh` und `update.sh` auf die gemeinsame Logik umstellen.
- [ ] Bei Rebuild laufenden HydraHive-Dienst vor dem Leeren stoppen.
- [ ] Tests grün ausführen.
- [ ] Commit: `fix(installer): Python-venv nach Distro-Upgrade selbst heilen`.

### Task 2: AgentLink-Rebuild absichern

- [ ] Test ergänzen, dass bei `--clear` vor dem Venv-Aufbau gestoppt wird.
- [ ] Test rot ausführen.
- [ ] `20-agentlink.sh` ergänzen.
- [ ] Tests grün ausführen.
- [ ] Commit/PR im hydralink-Repo und Merge in `main`.

### Task 3: PostgreSQL-Migration

- [ ] Guardrail-Tests für Root-Check, Backup, gzip-Prüfung, pgvector-Zielpaket,
  `pg_upgradecluster`, Verifikation, Collation-Refresh und Nicht-Löschen des
  alten Clusters schreiben.
- [ ] Tests rot ausführen.
- [ ] Migrationsskript implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(installer): gesicherte PostgreSQL-16-zu-18-Migration`.

### Task 4: Voice-Autostart

- [ ] Regressionstest für `boot.autostart=true` schreiben und rot ausführen.
- [ ] Autostart für STT und TTS idempotent setzen.
- [ ] Tests grün ausführen.
- [ ] Commit: `fix(voice): Incus-Container nach Host-Reboot automatisch starten`.

### Task 5: Echte Systemverifikation

- [ ] Snapshot `test24/post-2604-pre-repair` als definierten Ausgangspunkt
  verwenden.
- [ ] neuen Code auf den Testserver übertragen und `update.sh` ausführen.
- [ ] HydraHive- und AgentLink-venvs verwenden Python 3.14 und beide Dienste
  antworten gesund.
- [ ] PostgreSQL-Migrationsskript ausführen: 18/main auf Port 5432, alter
  16/main bleibt als gestoppter Rollback-Cluster erhalten.
- [ ] Voice-Container laufen und `boot.autostart=true`; äußerer Container-Reboot
  beweist Autostart.
- [ ] Sentinel-Projekt, Sentinel-Datei, Session, Benutzer und beide Datenbanken
  sind unverändert über API/SQL vorhanden.
- [ ] vollständige relevante Test-Suite und Shell-Syntaxprüfungen grün.

### Task 6: Review, Dokumentation und Merge

- [ ] Security-Review: keine PATH-Hijacks, kein ungeprüftes Löschen, Backups mit
  restriktiven Rechten, Fehler stoppen den Ablauf.
- [ ] HH-Review und `git diff`/`git status` prüfen; fremde Buddy-Dateien bleiben
  unberührt.
- [ ] Kunden-Runbook finalisieren: regulärer LTS-Kanal, kein `-d` in Produktion.
- [ ] Branch pushen, PR erstellen, CI abwarten und erst bei vollständigem Grün
  mergen.

## Akzeptanzkriterien

- [ ] Frische Installation bleibt auf Ubuntu 24.04 und 26.04 funktionsfähig.
- [ ] Dangling Venv wird erkannt und ohne manuelles Löschen repariert.
- [ ] Gesundes Venv wird nicht unnötig neu erstellt.
- [ ] AgentLink hat keinen systemd-Restart-Race während `--clear`.
- [ ] PostgreSQL-Backup wird vor der Migration erstellt und geprüft.
- [ ] Der alte PostgreSQL-Cluster wird niemals automatisch gelöscht.
- [ ] PostgreSQL 18 bedient nach Migration Port 5432 inklusive `vector`.
- [ ] Voice-Container überleben einen Host-Reboot per Autostart.
- [ ] Alle Sentinel-Daten bleiben erhalten.
- [ ] Kunden erhalten einen kopierbaren, fehlertoleranten Ablauf und einen
  klaren Rollback-Punkt.

## Nicht in diesem Plan

- Automatisches Ausführen von `do-release-upgrade` aus der HydraHive-Web-UI.
- Automatisches Löschen alter PostgreSQL-Cluster oder Backups.
- Allgemeine Container-Snapshot-UI; dafür existiert Task `e3172340`.
- Produktivupgrade vor erfolgreichem echten Testlauf und CI.
