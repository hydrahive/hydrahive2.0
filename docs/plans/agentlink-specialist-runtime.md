# Plan: Spezialisten-Laufzeiten und AgentLink-Zuverlässigkeit

## Audit-Basis

Aus 320 Handoff-Läufen der 13 Projektspezialisten:

- 23 Runner-Pausen durch `max_iterations` (7,2 %),
- 12 wahrscheinliche globale Run-Timeouts um 540 Sekunden,
- zahlreiche Provider-/Modellfehler,
- drei nominelle HydraHive-Code-Spezialisten ohne Datei- oder Shell-Tools.

Vier Projektspezialisten stehen noch auf 16 Iterationen; andere erreichen trotz 200–250 Iterationen Timeouts oder Pausen. Eine pauschale Erhöhung löst das Problem daher nicht.

## Phase 0: Fehlerantworten zuverlässig zustellen

Live-AgentLink akzeptiert für `task.status` nur `pending`, `in_progress`, `blocked`, `done`. HydraHive sendet bei Runnerfehlern derzeit `error`; der AgentLink-POST wird abgelehnt und der Caller wartet bis zum Timeout.

- [x] RED-Test: Receiver sendet Fehler als AgentLink-kompatibles `blocked`.
- [x] RED-Test: `ask_agent` wandelt nicht-`done` Antworten in `ToolResult.fail` um.
- [x] Teilausgabe und terminalen Fehlergrund gemeinsam zurückgeben.
- [x] Findings-Limit datensparsam von 2.000 auf höchstens 12.000 Zeichen anheben.
- [x] Bestehende Spoofing-/Timeout-/Receiver-Tests ausführen.

## Phase 1: Spezialisten-Defaults vollständig konfigurierbar

- [x] `config.create` und API-Create reichen `max_iterations`, Compaction und Live-Truncation wirklich durch.
- [x] `create_specialist`/`configure_specialist` exponieren validierte Runtimefelder.
- [x] Grenzen bleiben bei bestehenden Validatoren (u.a. max. 250 Iterationen, max. 200.000 Tokens).
- [x] Toolmengen bleiben auf die Rechte des Projekt-Agenten begrenzt.
- [x] UI-Default `max_tokens` an Backend-Default 16.384 angleichen.

## Phase 2: Auftragsbezogene Budgets

- [x] Profile `quick`, `standard`, `deep` spezifizieren (`docs/specs/agentlink-runtime-profiles.md`).
- [x] Per-Call-Budget darf den gespeicherten Spezialisten-Cap nie überschreiten.
- [x] Interne Runtime-Metadaten versioniert und AgentLink-kompatibel transportieren.
- [x] Timeout des Callers muss größer als der effektive Target-Timeout bleiben.
- [x] Keine per-call Erweiterung von Tools, Modell oder Rechten.

## Phase 3: Checkpoint, Resume und Arbeitsstatus

- [x] `max_iterations` als resumierbaren Checkpoint statt undifferenzierten Fehler transportieren.
- [x] Teilergebnis, Abbruchgrund, Sessionbezug und verbleibende Arbeit strukturiert zurückgeben.
- [x] Kontrollierte Fortsetzung derselben Specialist-Session ermöglichen.
- [x] Sessionbezug an die bestehende Activity-Anzeige anbinden; keine Antwort-Futures durch Zwischenstates auflösen.

## Phase 4: Bestehende Spezialisten

- [ ] 13 Projektspezialisten nach Rolle, Tools, Modell und Budget prüfen.
- [x] hydrahive-backend/frontend/media mit passenden, vererbbaren Tools ausstatten.
- [x] Fehlerhafte zentrale Modelle durch toolfähiges `openai-codex/gpt-5.6-sol` ersetzen.
- [ ] Profile mit realen Handoffs testen und Erfolgs-/Timeoutquote messen.

Rollout-Zwischenstand: Die fünf zentralen Spezialisten Security, Test, Backend,
Frontend und Media verwenden `openai-codex/gpt-5.6-sol`; reale Datei-Tool-Handoffs
waren erfolgreich. Die Runtime-Caps aller 13 Agenten werden nach Deployment dieser
Änderung über das dann erweiterte `configure_specialist` gesetzt und gemessen.

## Sicherheitsregeln

- Keine unbegrenzten Iterationen oder Timeouts.
- Externe Handoffs dürfen interne Caps nicht erhöhen.
- Projekt-Agenten dürfen nur eigene Rechte weiterreichen.
- Fehlerantworten müssen terminal, authentifiziert und eindeutig dem Ziel zugeordnet sein.
- Keine Taskinhalte in neuen Aggregatmetriken.

## Phase-0-Verifikation

- 46 AgentLink-, Handoff-, Spoofing-, Runner- und Integrity-Tests bestanden.
- Live-OpenAPI bestätigt die erlaubten AgentLink-Statuswerte `pending|in_progress|blocked|done`.
- Fehler werden transportkompatibel als `blocked`, intern weiterhin als `error` verbucht.
- Ruff, Compile und Diff-Prüfung bestanden.
