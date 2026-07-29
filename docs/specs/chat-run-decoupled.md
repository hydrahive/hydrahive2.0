# Plan: Agent-Lauf vom Browser entkoppeln (+ echter Stop)

## Ziel

Ein Agent-Lauf läuft serverseitig weiter, egal ob der Browser offen ist. Nach
dem Wiederverbinden kann der User den laufenden Lauf **stoppen** (nicht nur
zuschauen). PC aus / Browser zu → der Lauf läuft zu Ende.

## Problem (verifiziert)

`_session_msg_helpers.sse_run_with_guard()` konsumiert `runner_run()` **im
SSE-Generator** (`async for ev in gen: yield ev`). Reißt die HTTP-Verbindung
(Browser zu, PC aus, TCP-Timeout), bricht Starlette den Generator ab
(`GeneratorExit`/`CancelledError`) → der Run stirbt mitten drin.

Frontend: „Stop" = `AbortController.abort()` auf genau diese fetch-Verbindung
(useChat.ts:39). Nach Reconnect ist die Verbindung weg → Stop wirkt nicht mehr.

Das Concurrency-Modul kennt nur ein in-memory `set[str]` aktiver Session-IDs —
**keine Task-Referenz**, also kein gezieltes Canceln möglich.

## UX-Anforderung (till): flüssiges Token-Streaming MUSS erhalten bleiben

Kein „Antwort erscheint in Schüben". Deshalb NICHT der ping+reload-Weg, sondern
ein lückenloser **Event-Bus pro Session** (Ringpuffer mit Sequenznummer):
- Der entkoppelte Run ist der EINZIGE Producer und schreibt JEDES runner-Event
  (TextDelta, ToolUse, Done, …) mit fortlaufender `seq` in den Bus.
- Consumer (Sender-Stream UND Reconnect-Stream) lesen ab ihrem `seq`-Cursor
  weiter — kein Token geht verloren, auch bei Reconnect mitten im Lauf.
- Ringpuffer (z.B. letzte 2000 Events/Session) puffert für kurze Verbindungs-
  lücken; ist der Cursor rausgefallen, lädt der Client einmalig aus der DB nach
  und springt auf den aktuellen seq.

## Lösung (Muster existiert: `inject_message` nutzt `background_tasks.add_task`)

1. **Run als entkoppelter Server-Task**: `post_message`/`resend` starten den
   Runner als eigenständigen `asyncio.Task` (nicht im SSE-Generator). Der Task
   konsumiert `runner_run` bis zum Ende und schreibt wie gehabt in die DB +
   broadcastet Live-Pings. Verbindungsabbruch berührt ihn nicht.
2. **Task-Registry** (`runner/concurrency.py` erweitern): beim Start Task-Handle
   registrieren, `cancel(session_id)` bricht ihn ab, `finally` räumt auf.
3. **SSE nur noch Zuschauer**: `post_message` startet den Task und gibt sofort
   den `stream_session`-SSE zurück (Live-Sync). Der Stream liest nur mit; sein
   Abbruch killt den Run nicht mehr.
4. **Echter Stop-Endpunkt**: `POST /sessions/{id}/stop` → `cancel(session_id)`.
   Der Stop-Button ruft diesen Endpunkt statt die Verbindung zu kappen.
5. **Frontend**: `busy`/Stop-Zustand aus dem Server ableiten (Session-Status
   `running`), damit der Stop-Button auch nach Reconnect aktiv ist. `cancel`
   ruft `POST /stop` statt `AbortController.abort()`.

## Dateien

Backend:
- `core/src/hydrahive/runner/concurrency.py` — Task-Registry: `register_task`,
  `cancel`, `get_task`; `session_run_guard` optional mit Task-Handle.
- `core/src/hydrahive/api/routes/_session_msg_helpers.py` — neue
  `start_run_task()` (entkoppelt) statt `sse_run_with_guard` im Stream.
- `core/src/hydrahive/api/routes/sessions_messages.py` — `post_message`/`resend`
  starten Task + geben SSE zurück; neuer `POST /{id}/stop`; `stream_session`
  liefert initial `is_running`.
- `core/tests/test_run_decoupled.py` — Run überlebt „Verbindungsabbruch", Stop
  cancelt, kein Doppelstart.

Frontend:
- `frontend/src/features/chat/useChat.ts` — `cancel` ruft `POST /stop`; Run-Start
  entkoppelt (Response nicht mehr lebensnotwendig fürs Weiterlaufen); busy aus
  Server-Status beim Laden/Reconnect.
- `frontend/src/features/chat/api.ts` — `stopRun(sessionId)`.

## Implementierungsreihenfolge (TDD)

### Task 1: Task-Registry in concurrency.py
- [ ] Test: `register_task`/`get_task`/`cancel` — cancel bricht laufenden Task ab,
      `is_running` false nach Ende.
- [ ] Implementieren: `_tasks: dict[str, asyncio.Task]`; `cancel()` → `task.cancel()`.
- [ ] Guard erweitert: registriert den aktuellen Task, `finally` deregistriert.

### Task 2: Entkoppelter Run-Start
- [ ] Test: `start_run_task()` startet Run als Task; nach „Abbruch des
      Aufrufers" läuft der Task weiter bis Done (DB bekommt finale Assistant-Msg).
- [ ] Implementieren: `start_run_task(session_id, user_content)` →
      `asyncio.create_task(_run())`, registriert in Registry, 409 bei is_running.

### Task 3: post_message/resend entkoppeln + Stop-Endpunkt
- [ ] Test: `POST /messages` → Task läuft, Response-Abbruch killt Run NICHT.
- [ ] Test: `POST /{id}/stop` → Run wird gecancelt (is_running false, DB konsistent).
- [ ] Implementieren: post_message ruft start_run_task, gibt stream_session-SSE
      zurück; `POST /{id}/stop` → cancel; stream_session initial `{"t":"running",...}`.

### Task 4: Frontend Stop + Reconnect-Status
- [ ] `stopRun()` in api.ts; `cancel` in useChat ruft es.
- [ ] busy nach Laden/Reconnect aus Session-Status (running) — Stop-Button aktiv.
- [ ] tsc + eslint grün.

## Akzeptanzkriterien
- [ ] Aufgabe starten, Browser schließen, 10+ min → Run läuft weiter & wird fertig.
- [ ] Reconnect während Lauf → Stop-Button aktiv, Stop wirkt.
- [ ] Kein Doppelstart (409 bleibt), Concurrency-Guard intakt.
- [ ] Bestehende Chat-Tests grün, keine Regression im normalen Senden/Streamen.

## Nicht in diesem Plan
- Multi-Worker/DB-basierter Run-Status (bleibt in-memory, Single-Worker — wie heute).
- Persistente Wiederaufnahme nach Server-Neustart (Run überlebt Prozess-Restart NICHT).
- Voice-Bridge (nutzt eigenen Pfad, nicht betroffen).
