# Plan E4: Budget aus dem Template, Überschreitung, Antwort als Kurzfassung + Datei

Spec: `docs/specs/agent-templates.md` Kap. 7, 9 (Punkt 4). Voraussetzung: E3 live.

## Ziel

- Ein delegierter Spezialist bekommt das Budget **seines Templates**, nicht mehr min(Agent, Profil).
- Der Auftraggeber kann mit Begründung um höchstens `overrun_pct` überschreiten.
- Antworten werden nicht mehr in der Mitte abgeschnitten: Kurzfassung im Kontext, Langfassung als Datei.

## Bestand (main 51dfe1db)

- `agentlink/runtime_profiles.py`: `_PROFILE_CAPS` quick/standard/deep; `effective_budget(agent,
  profile)` = Minimum; `session_budget` liest `agentlink_runtime` aus den Sitzungs-Metadaten.
- `runner/_handoff_setup.py`: `prepare_handoff` → `effective_budget(target, profile_from_reason)`.
- `runner/runner.py` `_runtime_limits`.
- `tools/ask_agent.py`: Parameter `profile` (enum), `_response_timeout(target, profile)`.
- `runner/_handoff_reply.py` `bounded_reply` (12.000 Zeichen, ¾ Anfang + ¼ Ende); genutzt in
  `post_reply`, `delegation_watch.py`, `_delegation_record.py`.
- Tests: `test_agentlink_runtime_profiles.py`, `test_runner_runtime_profile_limits.py`,
  `test_handoff_*`, `test_agent_handoffs_resume.py`.

## Dateien

- `core/src/hydrahive/agentlink/runtime_profiles.py` – `effective_budget(agent, overrun=False)`:
  Basis = Template-Budget des Ziels; `overrun` → Basis × (1 + overrun_pct/100), gekappt an den
  Validierungsgrenzen. Version auf 2; v1-Metadaten laufender Sitzungen weiter lesbar.
- `core/src/hydrahive/agentlink/runtime_profiles.py` – Umschlag `hh-runtime:v2:overrun` statt Profilname.
- `core/src/hydrahive/runner/_handoff_setup.py` – Begründung in `agent_handoffs` speichern.
- `core/src/hydrahive/db/agent_handoffs.py` – Spalte `overrun_reason` (Migration, nullable).
- `core/src/hydrahive/tools/ask_agent.py` – `profile` entfernt (alte Werte toleriert + ignoriert, Warnung),
  neu `overrun: bool`, `overrun_reason: str` (Pflicht bei `overrun`, 10–500 Zeichen).
- `core/src/hydrahive/runner/_handoff_reply.py` – `bounded_reply` ersetzt durch `split_reply`:
  Kurzfassung (≤ `summary_max_chars` aus Template) + Langfassung als Datei.
- `core/src/hydrahive/runner/_handoff_report.py` (neu) – Langfassung schreiben unter
  `<Workspace des Auftrags>/.hydrahive/reports/<handoff_id>.md`, Pfad zurückgeben; ohne Workspace
  → Ablage im Agenten-Datenordner + Datei-Link über `/api/files`.
- System-Prompt-Baustein für Spezialisten (`runner/_delegation_message.py` bzw. Template-Antwortformat):
  „Antworte mit: Ergebnis · Belege · Offene Punkte. Ausführliches in die Langfassung.“
- Tests: `test_runtime_budget_template.py`, `test_ask_agent_overrun.py`, `test_handoff_split_reply.py`.

## Reihenfolge

### T1: Budget aus Template
- [ ] Tests: Ziel mit Template-Budget 96/32.768/1.800 → Sitzung bekommt genau das (vorher 32/16.384/540);
      Ziel ohne Template (Altbestand) → altes Verhalten; v1-Metadaten einer laufenden Sitzung werden
      weiter gelesen.
- [ ] RED → Umsetzung → GREEN, bestehende Profil-Tests angepasst. Commit.

### T2: Überschreitung
- [ ] Tests: `overrun=True` ohne Begründung → Werkzeugfehler; mit Begründung → Budget × 1,2 bei
      `overrun_pct=20`; `overrun_pct=0` → kein Effekt + Hinweis; Kappung an 250/200.000/3.600;
      Begründung steht in `agent_handoffs`.
- [ ] RED → Umsetzung → GREEN. Commit.

### T3: `ask_agent` umstellen
- [ ] Tests: Schema ohne `profile`; alter Aufruf mit `profile="deep"` läuft, wird ignoriert, Log-Warnung;
      `_response_timeout` aus Template (+ Überschreitung).
- [ ] RED → Umsetzung → GREEN. Commit.

### T4: Kurzfassung + Datei
- [ ] Tests: Antwort ≤ Grenze → unverändert, keine Datei; Antwort > Grenze → Kurzfassung = Abschnitt
      „Ergebnis“ (falls vorhanden) bzw. Anfang bis Grenze an Satzende, plus Zeile
      „Langfassung: <pfad>“; Datei enthält den **vollständigen** Text; nichts aus der Mitte fehlt.
      `delegation_watch` und `_delegation_record` nutzen dieselbe Funktion.
- [ ] RED → Umsetzung → GREEN. Commit.

### T5: Kürzungs-Rückfrage
- [ ] Test: Fehlt der Abschnitt „Ergebnis“ und ist die Antwort zu lang → Spezialist bekommt **einmal**
      die Bitte um eine Kurzfassung (ein zusätzlicher Modellaufruf, kein Werkzeug), danach wie T4.
- [ ] RED → Umsetzung → GREEN. Commit.

## Akzeptanzkriterien
- [ ] Spezialist mit Template-Budget 96 Iterationen bekommt bei Delegation 96.
- [ ] Überschreitung nur mit Begründung, höchstens `overrun_pct`, protokolliert.
- [ ] Keine Antwort wird mehr in der Mitte gekürzt; Langfassung als Datei erreichbar.
- [ ] Laufende Delegationen beim Update brechen nicht ab (v1 lesbar).

## Nicht in diesem Plan
- Briefing-Pflicht und Delegationsregeln (E6). Löschen von `_PROFILE_CAPS` (E7).
