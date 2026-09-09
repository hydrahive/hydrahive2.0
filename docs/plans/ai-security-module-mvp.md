# Plan: AI-Security-Modul — MVP-Adapter

## Ziel

Nach diesem Plan existiert ein optional installierbares HydraHive-Modul `ai-security`, das einen konfigurierten AI-Infra-Guard über einen sicheren, authentifizierten Adapter für AI-Infrastruktur-Scans nutzt. Scanstatus und Reports sind persistent, benutzerisoliert und werden über einen überwachten Moduljob aktualisiert.

## Dateien

- `core/src/hydrahive/settings/_ai_security.py` — zentrale, env/override-basierte Modulkonfiguration.
- `core/src/hydrahive/settings/settings.py` — neues Settings-Mixin einhängen.
- `modules/ai-security/manifest.json` — Modulvertrag, ohne automatische privilegierte Service-Installation.
- `modules/ai-security/backend/__init__.py` — Router, Migration und Polling-Job registrieren.
- `modules/ai-security/backend/config.py` — Allowlist- und Upstream-Konfiguration validieren.
- `modules/ai-security/backend/aig_client.py` — begrenzter AIG-HTTP-Client, keine freie URL.
- `modules/ai-security/backend/service.py` — DB-Zugriffe, Redaction und Statuslogik.
- `modules/ai-security/backend/routes.py` — authentifizierte Health-, Target- und Scan-Endpunkte.
- `modules/ai-security/backend/jobs.py` — begrenztes Status-/Result-Polling.
- `modules/ai-security/migrations/001_ai_security.sql` — Scan-Tabelle und Indizes.
- `modules/ai-security/tests/conftest.py` — isolierte Modul-Fixtures.
- `modules/ai-security/tests/test_config.py` — Allowlist- und URL-Grenzen.
- `modules/ai-security/tests/test_routes.py` — Auth, User-Isolation und API-Verträge.
- `modules/ai-security/tests/test_client.py` — Upstream-Request, Fehler, Timeout und Redaction.
- `modules/ai-security/tests/test_jobs.py` — Statusübergänge und Fehlerisolation.
- `modules/ai-security/frontend/index.tsx` — zunächst keine Navigation; Platzhalter für Phase 2 nur falls Build-Vertrag erforderlich.

## Implementierungsreihenfolge

### Task 1: Konfiguration und Datenmodell

- [x] Spec in `docs/specs/ai-security-module.md` schreiben.
- [x] Plan in `docs/plans/ai-security-module-mvp.md` schreiben.
- [x] Test schreiben: ungültige Origin, Userinfo, Pfad, Query und nicht erlaubtes Ziel werden abgewiesen.
- [x] Test ausführen: RED.
- [x] Settings-Mixin, Manifest und Migration implementieren.
- [x] Test ausführen: GREEN.
- [x] Gezielt committen: `feat(ai-security): add scanner module contract and storage`.

### Task 2: AIG-Client

- [x] Test schreiben: Task-Erstellung sendet nur `ai_infra_scan` und erlaubtes Ziel; API-Key-artige Felder werden redigiert; Fehler werden klassifiziert.
- [x] Test ausführen: RED.
- [x] Async-Client mit konfiguriertem Base-URL, Timeout und Response-Limit implementieren.
- [x] Test ausführen: GREEN.
- [x] Gezielt committen: `feat(ai-security): add bounded AI-Infra-Guard client`.

### Task 3: Authentifizierte API und Persistenz

- [x] Test schreiben: unauthenticated 401, 202 bei erfolgreicher Anlage, 503 bei Upstream-Fehler und Alice/Bob-Isolation.
- [x] Test ausführen: RED.
- [x] Health-, Targets-, Scan-Liste-, Scan-Erstellung- und Scan-Detail-Routen implementieren.
- [x] Test ausführen: GREEN.
- [x] Gezielt committen: `feat(ai-security): expose authenticated scan API`.

### Task 4: Polling-Job

- [x] Test schreiben: `pending/running/completed/failed`, Result-Download nur einmal, einzelner fehlerhafter Scan isoliert.
- [x] Test ausführen: RED.
- [x] Job registrieren und Status-/Result-Polling mit Limit und Fehlerklassen implementieren.
- [x] Test ausführen: GREEN.
- [x] Gezielt committen: `feat(ai-security): poll scanner jobs safely`.

### Task 5: Dokumentation und Integrationsprüfung

- [x] Modul-README mit Installation, Konfiguration, Betriebsgrenzen und Upstream-Attribution schreiben.
- [x] Modul-Test-Suite und relevante Core-Tests ausführen.
- [x] HydraHive-spezifisches Review durchführen: Dateigrößen, Settings-Singleton, keine Prints/hardcodierten Pfade, Importzyklen.
- [x] Security-Audit durchführen: Auth, SSRF-/Allowlist-Grenzen, Response-Limits, keine Secrets, keine privilegierte Service-Installation.
- [x] Frontend-Build/Modulgenerator prüfen; UI bleibt in separatem Phase-2-Task.
- [x] Gezielt committen: `feat(ai-security): add bounded AI infra scanner module`.

## Akzeptanzkriterien

- [ ] Modul lädt auch ohne laufenden AIG-Dienst.
- [ ] Nur konfigurierte Origins sind scanbar.
- [ ] Nur Scanbesitzer sehen Status und Report.
- [ ] AIG-Task-API wird korrekt und begrenzt angesprochen.
- [ ] Große/ungültige Upstream-Antworten werden sicher behandelt.
- [ ] Polling-Fehler eines Scans stoppen keine anderen Moduljobs.
- [ ] Keine automatische Aktivierung von `SYS_ADMIN`, `seccomp:unconfined` oder öffentlichem Port.
- [ ] Tests und Projekt-Checks sind vor Abschluss frisch verifiziert.

## Nicht in diesem Plan

- MCP-/Skill-Upload und Archivverarbeitung.
- Agent-Scan, Jailbreak-Evaluation oder andere aktive Tests.
- UI-Dashboard und automatische Hub-Veröffentlichung.
- Docker-Stack-Installation des Upstreams.
- automatische Remediation.
