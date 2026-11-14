# Delegations-Zuverlässigkeit

Diagnose vom 14.11.2026 (Till): Buddy hat eine ganze Arbeitssession lang (Agenten-Templates + Agenten-Büro,
~20h Code-Arbeit) kein einziges Mal `ask_agent` zur echten Delegation benutzt — alles selbst direkt per
Shell/Datei-Tools im Worktree erledigt, trotz der eigenen Arbeitsweise-Regel im System-Prompt
("Arbeit, die zu einem Projekt gehört, gibst du an den Projekt-Agenten ab"). Zwei Ursachen identifiziert:

1. **Diszipliniert-sein reicht nicht** — die Regel ist nur eine Bitte im Prompt, kein technisches Limit.
2. **Delegation ist zu unzuverlässig, um sich zu lohnen** — E6-Messung (31.10.–14.11.): von 33 Delegationen
   nur 17 `done`, 48 % `lost`/`error`/`timeout`/`paused`/`cancelled`.

Till: „Im Hydrahive-DEV-Projekt hat das parallele Arbeiten mit mehreren Agenten eine Zeit lang gut geklappt,
ist aber immer weniger geworden." Diese Spec behandelt **Ursache 2** (Zuverlässigkeit). Ursache 1 (harte
Tool-Policy statt Prompt-Bitte) ist ein Folge-Vorhaben, siehe Kapitel 6.

## 1. Befund: warum Delegationen verloren gehen

Code-Analyse (main e5a036b6):

### 1.1 Watcher leben nur im Prozess-Speicher

`runner/delegation_watch.py`: `_tasks: dict[str, asyncio.Task] = {}` — eine reine In-Memory-Map. Jeder
Server-Neustart (Deploy, Crash, `--reload`) verwirft alle laufenden Watcher-Tasks ersatzlos.

### 1.2 Die Aufräum-Routine kennt nur „weg", nicht „fortsetzen"

`db/delegations.py::reconcile_on_start()` (aufgerufen aus `api/lifespan.py::_setup_background_delegations`)
setzt beim Start technisch korrekt alle noch `running` stehenden Delegationen auf `status='lost'`. Das
funktioniert wie gebaut — das Problem ist das Verhalten selbst: **jeder Neustart während einer laufenden
Delegation killt sie unwiderruflich**, auch wenn der Zielagent kurz vor dem Abschluss stand.

Parallel dazu `runner/handoff_receiver.py::reconcile_orphaned_handoffs()`: verwaiste `agent_handoffs`-Zeilen
(Status `running`) werden beim Start auf `error` gesetzt — dieselbe Grundannahme.

### 1.3 Der Shutdown-Pfad nutzt den vorhandenen Checkpoint-Mechanismus nicht

Für reguläre Budget-Überschreitung (`max_iterations`) gibt es bereits einen Checkpoint/Resume-Weg:
`agentlink/checkpoints.py::checkpoint_finding()` erzeugt ein `resume_token`, der Handoff wird `paused`
statt `error`, und ein späterer `ask_agent`-Aufruf mit `resume_token=...` setzt genau diese Session fort
(`runner/_handoff_setup.py::_resume_session`).

Im `asyncio.CancelledError`-Zweig von `handoff_receiver.py` (ausgelöst durch Server-Stopp/Reload während
ein Handoff läuft) passiert das **nicht**: Es wird eine `error`-Antwort gepostet, `agent_handoffs` auf
`error` gesetzt — aber `record_delegation_result()` wird hier nicht aufgerufen, die zugehörige
`agent_delegations`-Zeile bleibt auf `running` stehen, bis sie beim nächsten Start von
`reconcile_on_start()` auf `lost` fällt. Kein Resume-Token, keine Fortsetzungsmöglichkeit — die bereits
geleistete Arbeit des Spezialisten ist komplett weg.

### 1.4 Feste Timeouts ohne Rücksicht auf die Aufgabe

`HH_AGENTLINK_RUN_TIMEOUT` (Default 540s) und `HH_AGENTLINK_HANDOFF_TIMEOUT` (Default 600s) sind global,
unabhängig von der Art der Aufgabe. Eine volle Backend-Testreihe allein dauert heute schon ~5 Minuten
(gemessen während der Arbeit an #712–#715) — bei Spezialisten, die Tests laufen lassen UND danach noch
etwas tun sollen, ist das knapp.

### 1.5 Der Teufelskreis

Je aktiver am System selbst gebaut wird (häufige Deploys/Neustarts, genau die Phase, in der Delegation
am meisten genutzt werden sollte), desto mehr Delegationen fallen auf `lost`. Das erklärt Tills
Beobachtung „hat mal gut geklappt, wird immer weniger" — es korreliert nicht mit schlechteren Agenten,
sondern mit der Deploy-Frequenz.

## 2. Vergleich: wie OpenClaw das löst

Recherche 14.11.2026 (docs.openclaw.ai). Relevante Unterschiede zu unserem Stand:

- **Push statt Pull**: `sessions_spawn` ist nicht-blockierend, `sessions_yield` beendet den aktuellen Zug
  und wartet auf das Abschluss-Ereignis — kein Polling. Wir haben das im Grundprinzip schon
  (`delegation_delivery.kick`), das ist nicht die Lücke.
- **Strukturierte Sichtbarkeit ohne Nachfrage**: ein `Active Subagents`-Prompt-Block wird automatisch
  eingefügt, wenn Unteragenten laufen — der Auftraggeber muss nicht fragen. Teil-Deckung durch unser
  Agenten-Büro (`docs/specs/agent-office.md`), aber nicht im Prompt-Kontext des Auftraggebers selbst.
- **Kaskadierendes Beenden + Wiederherstellung nach Neustart ist ausdrücklich beschrieben**: „Nach einem
  Neustart des Gateways werden wiederhergestellte, veraltete und nicht beendete Läufe entfernt, sofern
  ihre untergeordnete Sitzung nicht als `abortedLastRun: true` gekennzeichnet ist [...] aktuelle
  untergeordnete Sitzungen erhalten eine synthetische Fortsetzungsnachricht, bevor die Abbruchmarkierung
  gelöscht wird." — das ist genau die Lücke, die wir schließen wollen (Kapitel 3.2).
- **Harte Tool-Policy auf Gateway-Ebene** statt Prompt-Bitte (Ursache 1, nicht Teil dieser Spec).

## 3. Lösung

### 3.1 Graceful Shutdown für laufende Handoffs (statt sofort killen)

Beim geplanten Server-Stopp (Lifespan-Shutdown, nicht Crash) laufenden Handoffs eine kurze Frist geben,
sich selbst zu beenden, bevor hart abgebrochen wird:

- `api/lifespan.py`: vor dem harten Shutdown `db_agent_handoffs.list_active()` lesen; für jede aktive
  Session über `runner.concurrency` signalisieren, den aktuellen Tool-Zug abzuschließen und dann zu
  stoppen (kooperativ, kein `task.cancel()` sofort).
- Frist: wenige Sekunden (z. B. 10s), danach normaler harter Cancel wie heute — kein unbegrenztes
  Warten, das den Deploy blockiert.

### 3.2 CancelledError-Pfad erzeugt einen Checkpoint statt „error"

In `handoff_receiver.py` im `asyncio.CancelledError`-Zweig: statt einer terminalen `error`-Antwort einen
Checkpoint wie beim `max_iterations`-Pfad erzeugen (`checkpoint_finding()`, Status `paused`,
`resume_token`). `record_delegation_result()` **wird** hier aufgerufen (fehlt heute), mit Status `paused`
und dem `resume_token` im Text, damit die aufrufende Session die begonnene Arbeit fortsetzen kann statt
komplett neu zu beauftragen.

### 3.3 Automatische Fortsetzung nach dem Neustart (statt nur `lost`)

`reconcile_on_start()` erweitern: Zeilen, die durch 3.2 einen `paused`-Checkpoint mit `resume_token`
bekommen haben, NICHT auf `lost` setzen. Für die übrigen (echter Crash/SIGKILL ohne Checkpoint — der
Normalfall bei `reconcile_on_start` bleibt unverändert `lost`, da hier keine saubere Zwischenablage
existiert und ein automatischer Resume-Versuch auf undefiniertem Zustand riskanter ist als eine ehrliche
Fehlermeldung.

Zusätzlich: Dem Auftraggeber beim nächsten Lauf-Ende der Session eine klare, umsetzbare Nachricht statt
nur „verloren" — bei `paused` mit Resume-Token den Hinweis, dass ein `ask_agent`-Aufruf mit
`resume_token=...` die begonnene Arbeit fortsetzt (Spiegel zum bestehenden `max_iterations`-Text).

### 3.4 Timeout-Diagnose

`HH_AGENTLINK_RUN_TIMEOUT`/`HH_AGENTLINK_HANDOFF_TIMEOUT` bleiben globale Fallbacks, aber: Templates mit
umfangreichen Testläufen (z. B. `reviewer`, `backend`) bekommen ein höheres Timeout-Feld im Template
selbst (`agent-templates.md` kennt schon ein Budget-Kapitel) statt eines einzigen globalen Werts. Diese
Spec ändert dafür nur die Lesestelle (`effective_timeout` zieht zuerst das Template-Feld, dann den
globalen Fallback) — die Template-UI/Admin-Oberfläche selbst ist bereits aus den Agenten-Templates-
Etappen vorhanden.

## 4. Datenmodell-Änderungen

Keine neue Tabelle. `agent_delegations` kennt `status` bereits inkl. `paused`
(aus Kapitel 3.2 — bisher nur über den `max_iterations`-Pfad erreicht, jetzt auch über den
Shutdown-Pfad). Kein Schema-Änderung nötig.

## 5. Nicht in dieser Spec

- Harte Tool-Policy (Ursache 1) — eigenes Vorhaben, siehe Kapitel 6.
- Umbau des Push/Yield-Mechanismus — funktioniert im Grundprinzip bereits (`delegation_delivery.kick`).
- Agenten-Büro-Integration der Checkpoint-Information — optionale spätere Ergänzung zur bereits
  gemergten Spec `agent-office.md`.

## 6. Folge-Vorhaben (nicht Teil dieser Spec)

**Harte Tool-Policy statt Prompt-Bitte** (Ursache 1): Buddy/Projekt-Agenten in Projekt-Kontexten auf
`ask_agent`-only beschränken (kein direktes `shell_exec`/`file_write` am Projekt-Repo), analog zu
OpenClaws `tools.allow`/`tools.deny` auf Gateway-Ebene. Erst angehen, wenn diese Spec (Zuverlässigkeit)
umgesetzt und eine Weile gelaufen ist — sonst hängt alles noch mehr an einem löchrigen Delegationsweg.

## 7. Etappen

1. Graceful Shutdown (3.1) + Checkpoint im CancelledError-Pfad (3.2). TDD. Ein PR.
2. Reconciliation erweitern: `paused` mit Resume-Token wird nicht mehr zu `lost` (3.3) +
   Hinweistext für den Auftraggeber. TDD. Ein PR.
3. Timeout aus dem Template statt nur global (3.4). TDD. Ein PR.
4. Eine Woche beobachten (Messung wie `scripts/measure_delegation.py`, Vorher/Nachher-Vergleich analog
   zur E6-Messung), dann entscheiden, ob Kapitel 6 (harte Tool-Policy) angegangen wird.

## 8. Akzeptanzkriterien

- [ ] Ein geplanter Server-Neustart während einer laufenden Delegation führt nicht mehr automatisch zu
      `lost`, wenn der Zielagent die Chance bekam, sauber zu pausieren.
- [ ] Nach dem Neustart kann die aufrufende Session die pausierte Arbeit per `resume_token` fortsetzen,
      ohne den Auftrag komplett neu zu formulieren.
- [ ] Ein echter Absturz (SIGKILL, kein geplanter Shutdown) landet weiterhin ehrlich auf `lost` —
      kein Resume-Versuch auf undefiniertem Zustand.
- [ ] Die Fehlerquote (lost+error+timeout / alle Delegationen) sinkt in der Nachher-Messung spürbar
      gegenüber den 48 % aus der E6-Messung vom 14.11.2026, besonders an Tagen mit vielen Deploys.
