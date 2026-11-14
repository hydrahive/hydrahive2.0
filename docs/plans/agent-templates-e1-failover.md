# Plan E1: Failover härten

Spec: `docs/specs/agent-templates.md` Kap. 8. Task 27b2b8d8 (+ e813b45f).
Unabhängig von den Templates, eigener PR, wirkt sofort auf alle Agenten mit `fallback_models`.

## Ziel

Fällt ein Modell wegen Timeout, Stream-Abbruch oder leerer Antwort aus, versucht der Lauf das nächste
Modell der Kette, statt abzubrechen. Gestörte Modelle werden kurz übersprungen. Jeder Wechsel ist in der
Sitzung sichtbar.

## Bestand (main 51dfe1db)

- `runner/_failover.py` `should_failover(exc) -> bool`: Regex über den Fehlertext, nur
  401/402/429/529, auth, quota, rate-limit, overload, billing, expired.
- `runner/_call.py` `call_with_stream_or_fallback`: Stream nur auf `models[0]`, bis zu
  `STALL_ATTEMPTS` (5) Versuche bei `_CONNECTION_ERRORS`, sonst 1 Wiederholung; danach
  Nicht-Streaming über alle Modelle; Wechsel nur wenn `should_failover(e)`.
  `_call_with_connection_retry` wiederholt Verbindungsfehler bis 5× und **wirft dann** – kein Wechsel.
- `runner/runner.py` ~Z. 349: leere Antwort → `Error(...)`, Lauf endet (`abandoned`).
- `compaction/_llm.py` nutzt `should_failover` ebenfalls (`should_switch_model`).
- Tests: `test_failover_decision.py`, `test_call_stall_retry.py`, `test_compaction_failover.py`,
  `test_codex_stream_errors.py`, `test_tool_gate_non_tool_models.py`.

## Dateien

- `core/src/hydrahive/runner/_failover.py` – Kategorien statt bool, Sperrzeit-Speicher.
- `core/src/hydrahive/runner/_call.py` – Timeout-Wechsel, leere Antwort, Sperrzeit, Ereignis.
- `core/src/hydrahive/runner/events.py` – neues Ereignis `ModelSwitch`.
- `core/src/hydrahive/runner/runner.py` – Ereignis speichern/weiterreichen; leere Antwort erst nach
  erschöpfter Kette als Fehler.
- `frontend/src/features/chat/…` – Hinweis „Modell gewechselt: A → B (Grund)“ in der Blase
  (Ort beim Bau über `grep used_model` bestimmen; Fußzeile zeigt das Modell heute schon).
- i18n `de`/`en` für den Hinweis.
- Tests: `core/tests/test_failover_categories.py`, `core/tests/test_call_failover_chain.py`.

## Reihenfolge

### T1: Fehlerkategorien
- [ ] Test `test_failover_categories.py`: `classify(exc)` liefert `auth|quota|rate_limit|overload|
      timeout|stream_abort|None`. Fälle: alle bisherigen Muster (aus `test_failover_decision.py`
      übernehmen), `httpx.ReadTimeout`, `httpx.ConnectTimeout`, `CodexStreamStall`,
      `asyncio.TimeoutError`, `httpx.RemoteProtocolError` → `stream_abort`; `ValueError("x")` → None;
      „line 402“ und „credentials“ bleiben None (bestehende Fehlalarm-Fälle).
- [ ] RED.
- [ ] `classify` in `_failover.py`; `should_failover(exc)` bleibt als
      `classify(exc) in {auth, quota, rate_limit, overload}` erhalten (Kompaktierung unverändert).
- [ ] GREEN, alter `test_failover_decision.py` grün.
- [ ] Commit `feat(runner): Fehlerkategorien für Modellwechsel`.

### T2: Timeout/Verbindungsabbruch wechselt das Modell
- [ ] Test in `test_call_failover_chain.py`: Kette `[A, B]`; Stream A wirft 5× `ReadTimeout`,
      Nicht-Streaming A wirft 5× `ReadTimeout` → B antwortet, `CallResult.model == B`.
      Gegenprobe: Kette `[A]` → Fehler wird geworfen wie bisher.
- [ ] RED.
- [ ] In der Nicht-Streaming-Schleife: Fehler aus `_call_with_connection_retry` mit Kategorie
      `timeout|stream_abort` → nächstes Modell (nicht beim letzten).
- [ ] GREEN, `test_call_stall_retry.py` grün (Wiederholversuche je Modell bleiben 5).
- [ ] Commit `feat(runner): Modellwechsel nach Timeout und Verbindungsabbruch`.

### T3: Leere Antwort wechselt das Modell
- [ ] Test: Kette `[A, B]`; Stream A liefert `message_stop` mit `blocks=[]` bzw. nur `thinking` →
      kein Text an die Oberfläche → Wechsel zu B. Kette `[A]` → `CallResult` mit leeren Blöcken wie
      bisher (runner meldet dann den bekannten Fehler).
- [ ] Gegenprobe: Hat A schon Text gestreamt, wird **nicht** gewechselt.
- [ ] RED.
- [ ] Prüfung `has_visible_content` (aus runner) in `_call.py` nach Stream-Ende und nach
      Nicht-Streaming-Antwort; leer und nicht letztes Modell → nächstes.
      Vorher **einmal** dasselbe Modell erneut (Vorschlag e813b45f), dann wechseln.
- [ ] GREEN.
- [ ] Commit `feat(runner): leere Antwort führt zum nächsten Modell`.

### T4: Kette auch im Streaming-Pfad
- [ ] Test: Kette `[A, B]`; A wirft beim Stream `429` vor dem ersten Text → B wird **gestreamt**
      (Fake zählt `stream_calls` für B ≥ 1), nicht sofort Nicht-Streaming.
- [ ] RED.
- [ ] Streaming-Versuch als Schleife über die Modelle: pro Modell bisherige Wiederholregel; bei
      Wechselgrund und `text_sent == False` → nächstes Modell streamen. Nicht-Streaming nur noch bei
      `StreamingNotSupported` bzw. als letzter Versuch.
- [ ] GREEN, alle `_call`-Tests grün.
- [ ] Commit `feat(runner): Modellkette auch beim Streaming`.

### T5: Sperrzeit für gestörte Modelle
- [ ] Test: `mark_down(model, category, seconds)` / `is_down(model, now)`; nach Ausfall mit
      `quota|auth|overload` wird A beim nächsten Aufruf übersprungen, solange die Sperre läuft;
      nach Ablauf wieder versucht. Sind **alle** gesperrt, wird trotzdem das erste versucht
      (nie „gar nichts“). `timeout|empty` sperren nicht.
- [ ] RED.
- [ ] Speicher im Prozess (`dict[model] -> until`), Standard 300 s, Parameter `cooldown_seconds`
      (in E2 aus dem Template).
- [ ] GREEN.
- [ ] Commit `feat(runner): gestörte Modelle kurz überspringen`.

### T6: Wechsel sichtbar machen
- [ ] Test: `call_with_stream_or_fallback` liefert `ModelSwitch(from_model, to_model, reason)` vor dem
      Ergebnis; runner reicht es durch und speichert es in den Metadaten der Assistenz-Nachricht
      (`model_switches: [...]`).
- [ ] RED → Umsetzung → GREEN.
- [ ] Frontend: Hinweis unter der Blase, i18n de/en. Vitest für die Anzeige.
- [ ] Commit `feat(chat): Modellwechsel in der Antwort anzeigen`.

## Akzeptanzkriterien
- [ ] Je Kategorie (429, Quota, Timeout, Stream-Abbruch, leere Antwort) ein Test, in dem B antwortet.
- [ ] Kein doppelter Text: nach gesendetem Text kein Wechsel.
- [ ] Alle bisherigen Runner-/Compaction-Tests grün, `ruff` sauber.
- [ ] Live auf hydratest: Agent mit Kette `[ungültiges Modell, gültiges]` antwortet, Hinweis sichtbar.

## Nicht in diesem Plan
- Templates, Seite, Budget (E2–E4). Die Kette kommt hier noch aus `llm_model` + `fallback_models`.
- Persistente Sperrzeit über Neustarts.
