# Plan: Agent Integrity — Evidenz bei direkten Fortsetzungen

## Problem

`IntegrityState` wird für jeden neuen User-Turn neu erzeugt. Dadurch werden sachlich korrekte Statusaussagen in direkten Fortsetzungen (`weiter`, `auf welchem Stand sind wir?`) als unbelegt markiert, obwohl der unmittelbar vorherige Turn Datei-, Commit- oder Testevidenz gespeichert hat. Die ersten strukturierten Live-Daten bestätigen diesen Fehlalarm für `fixed`, `implemented` und `tested`.

## Design

- Nur konservativ erkannte Fortsetzungs- und Statusprompts dürfen Evidenz übernehmen.
- Geladen wird ausschließlich der neueste Integrity-Snapshot derselben Session innerhalb von 24 Stunden.
- Die Abfrage selektiert nur Zeitstempel und Metadaten, niemals Nachrichteninhalt.
- Ein frischer oder unklarer Auftrag beginnt weiterhin ohne Evidenz.
- Übernommene Evidenz erzeugt einmalig das Beobachtungssignal `evidence_continued`.
- Eine neue Artefaktänderung invalidiert ältere Test-, Commit- und Push-Evidenz. Dadurch kann übernommene Evidenz nicht nach nachfolgenden Änderungen veralten.
- Kein Prompt-Zuwachs, kein zusätzlicher LLM-Aufruf und kein Enforcement.

## Dateien

- `core/src/hydrahive/runner/integrity_continuity.py` — konservative Klassifikation und Metadatenabruf.
- `core/src/hydrahive/runner/integrity.py` — Initialevidenz und kausale Invalidierung.
- `core/src/hydrahive/runner/integrity_evidence.py` — bekannte Evidenzarten zentral definieren.
- `core/src/hydrahive/runner/runner.py` — Continuity-Wiring vor dem Agentloop.
- `core/src/hydrahive/runner/integrity_metrics.py` — Continuity-Signal aggregieren.
- zugehörige Runner-, Metrics- und API-Tests.

## Tasks

### 1. Klassifikation und Laden

- [x] RED-Tests für positive deutsche/englische Fortsetzungen schreiben.
- [x] RED-Tests für neue, negierte und mehrdeutige Aufträge schreiben.
- [x] Session-Isolation, 24h-Grenze und malformed Metadaten testen.
- [x] Metadaten-only Query implementieren.

### 2. Evidenzlebenszyklus

- [x] Initialevidenz in `IntegrityState` unterstützen.
- [x] `evidence_continued` genau einmal persistieren.
- [x] Tests/Commit/Push nach neuer Artefaktänderung invalidieren.
- [x] Claim-Verifikation nach Fortsetzung und Änderung testen.

### 3. Runner und Metrik

- [x] Continuity-Helfer im Runner verdrahten.
- [x] Signal in Admin-Aggregaten sichtbar machen.
- [x] Legacy-Metadaten ohne Continuity weiter akzeptieren.

### 4. Abschluss

- [x] Integrity-, Runner-, Metrics-, API-, Auth- und Cache-Tests ausführen.
- [x] Ruff, Compile, HH- und Security-Review ausführen.
- [x] Prompt-Zuwachs 0 bestätigen.
- [ ] PR, CI, Merge und Live-Smoke-Test abschließen.

## Akzeptanzkriterien

- [x] Direkte Fortsetzungen können aktuelle Evidenz derselben Session verwenden.
- [x] Neue oder unklare Aufträge erben keine Evidenz.
- [x] Evidenz aus anderen Sessions oder älter als 24h wird nie übernommen.
- [x] Änderungen invalidieren kausal veraltete Qualitätsnachweise.
- [x] Keine Inhalte, Argumente, Outputs oder Identifikatoren gelangen in Admin-Metriken.

## Vorab-Verifikation

- 91 fokussierte Integrity-, Continuity-, Runner-, Metrics-, API-, Cache- und Auth-Tests bestanden.
- Gesamter Ruff-Lauf über `core/src` und `core/tests` bestanden.
- Compileall und `git diff --check` bestanden.
- Der lokale vollständige Pytest-Lauf erreichte das konfigurierte 300-Sekunden-Limit ohne gemeldeten Testfehler; der vollständige Lauf wird deshalb durch die obligatorische PR-CI bewertet, ohne einen weiteren blockierenden Watch-Lauf zu starten.
- Security-Review: Same-Session-Query, 24h-Grenze, bekannte Evidenz-Allowlist, Metadaten-only SELECT und keine neuen Response-Identifikatoren.
- HH-Review: Continuity in eigenem 80-Zeilen-Modul, Runner-Wiring klein, keine Prompt- oder Endpoint-Kopplung, Legacy-Snapshots bleiben gültig.
