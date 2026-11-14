# Plan E6 + E7: Feste Arbeitsweise und Aufräumen

Spec: `docs/specs/agent-templates.md` Kap. 9, 11. Voraussetzung: E4 live.

## E6 – Arbeitsweise in der Hierarchie

### Ziel
Buddy → Projekt-Agent → Spezialisten arbeiten nach festen Regeln, der Kontext des Projekt-Agenten
bleibt klein. Gilt für alle Projekte (keine Testphase in einem einzelnen Projekt, Till 14.11.).

### Messung vorher (vor dem ersten E6-Merge)
- [ ] Skript `scripts/measure_delegation.py` (nur lesen, sessions.db/PG-Spiegel, letzte 14 Tage):
      je Projekt-Agent Tokens je abgeschlossener Sitzung, `ask_agent`-Anteil an Werkzeugaufrufen,
      Ø/max Kontext, Fehlerquote delegierter Aufträge, Anteil Modellwechsel (aus E1).
- [ ] Ergebnis als `_work/messung/delegation-vorher-<datum>.md` ablegen.

### Dateien
- `core/src/hydrahive/tools/ask_agent.py` – Briefing-Felder `goal`, `known`, `deliverable`, `files`;
  `goal` + `deliverable` Pflicht (Fehlertext erklärt, was fehlt). `task` bleibt als Freitext.
- `core/src/hydrahive/runner/_delegation_message.py` – Briefing als fester Block in den
  Auftrag des Spezialisten.
- `core/src/hydrahive/runner/system_prompt.py` – Baustein „Arbeitsweise“ je Template-Gruppe:
  - Buddy: nimmt an, klärt, gibt Projektarbeit an den Projekt-Agenten.
  - Projekt-Master: plant, verteilt, prüft; Lesen vieler Dateien/Logs/Testläufe und Umsetzung → Spezialist.
  - Spezialist: arbeitet den Auftrag ab, antwortet im Antwortformat (E4).
  Text in eigener Datei `runner/_working_style.py`, i18n-fähig, nicht im Agent-Prompt.
- `core/src/hydrahive/runner/_handoff_setup.py` – Folgeauftrag an denselben Spezialisten im selben
  Vorgang (gleiche `incoming`-Kette / Sitzung des Auftraggebers) setzt dessen Sitzung fort statt neu.
- Security auf Abruf: Template-Feld `on_demand: true`; `ask_agent` an ein solches Template nur mit
  `task_type="review"` und Begründung, sonst Hinweis.
- Tests: `test_ask_agent_briefing.py`, `test_working_style_prompt.py`, `test_handoff_continue_session.py`,
  `test_on_demand_template.py`.

### Reihenfolge
- T1 Briefing-Pflicht (Test → RED → GREEN → Commit)
- T2 Briefing-Block beim Spezialisten
- T3 Arbeitsweise-Baustein im System-Prompt (Cache-stabil: im stabilen Teil, nicht im volatilen)
- T4 Sitzung fortsetzen
- T5 Security auf Abruf

### Messung nachher
- [ ] 14 Tage nach Live-Gang dasselbe Skript → `delegation-nachher-<datum>.md`, Vergleich an Till.

### Akzeptanzkriterien
- [ ] `ask_agent` ohne `goal`/`deliverable` wird abgelehnt, mit beiden ausgeführt.
- [ ] Prompt-Cache-Treffer des Projekt-Agenten nicht schlechter als vorher (Messung).
- [ ] Folgeauftrag nutzt dieselbe Spezialisten-Sitzung.

## E7 – Aufräumen

### Ziel
Alte Wege entfernen, sobald E3–E6 vier Wochen ohne Rückweg-Bedarf laufen.

- [ ] Agent-Configs: Felder `llm_model`, `fallback_models`, `max_iterations`, `max_tokens`,
      `handoff_timeout_seconds`, `reasoning_effort`, `compact_threshold_pct`, `cache_ttl`,
      `compact_model` entfernen (Skript mit Sicherung, wie E3 T2).
- [ ] Code: Lese-Pfade dieser Felder im Runner entfernen; `_PROFILE_CAPS` und
      `profile_from_reason` entfernen; v1-Metadaten nicht mehr lesen.
- [ ] `llm.json`: `default_model`/`lessons_model` nur noch Lese-Fallback für Systemrollen ohne Template,
      dann entfernen; `zahnfee.json` Feld `model` entfernen.
- [ ] `OPTIONAL_TOOLS`/Validierung: alte Feldnamen in Agent-Configs tolerieren, aber ignorieren.
- [ ] Doku: Hilfe-Seiten LLM + Agenten, Handbuch-Beitrag „LLM & Modelle“ / „Agenten“ (auf .2).
- [ ] Tests: alte Felder in einer Config → werden ignoriert, kein Fehler.

### Akzeptanzkriterien
- [ ] `git grep -n "fallback_models\|_PROFILE_CAPS"` in `core/src` nur noch in der Migrations-/
      Toleranzlogik.
- [ ] Alle Tests grün, hydratest und .2 laufen nach Update ohne Eingriff.
