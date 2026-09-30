# Lauf-Abbrüche sichtbar machen (refusal + Buddy-Fehleranzeige)

Task 891f1d3a. Freigabe Till am 30.09.2026: Teil a und b in einem PR, Teil c als eigener Task (71663ae3).

## Befund (Faktencheck 30.09.2026)

- Am 27.09.2026 endeten in der Buddy-Session 01a09709 zwei Läufe mit `stop_reason=refusal`.
  Die Antwort bestand nur aus einem thinking-Block. Till sah keinen Hinweis.
- Der Runner meldet leere Antworten seit ea1a6099 (13.07.2026) mit einer allgemeinen Meldung
  („leere Antwort“). Eine eigene refusal-Meldung gibt es nicht, und es entsteht kein
  `errors_log`-Eintrag.
- Seit Juni gab es 15 refusals. 3 davon hatten schon Text oder Tool-Aufrufe. Diese Läufe
  galten als „completed“ oder liefen mit den Tools weiter, ohne Hinweis.
- Die Buddy-Seite nutzt `chat.error` nur für die Maskottchen-Stimmung. Der Text wird nicht
  angezeigt, und der Button „Weitermachen“ bei max_iterations fehlt ebenfalls.
- `useChat.reload()` löscht den Fehler bei jedem Reload (außer bei max_iterations). Nach jedem Lauf
  sendet der Server einen Live-Sync-Ping (`{"t":"done"}`), der einen Reload auslöst. Dieses Muster
  ist in c8c591a7 für max_iterations belegt („Banner blinkt weg“). Andere Fehler verschwinden
  dadurch oft kurz nach dem Anzeigen.

## Änderungen

### a) Runner (core)

- `stop_reason == "refusal"` beendet den Lauf immer, auch wenn Text oder tool_use vorhanden ist.
- Angefangene tool_use-Blöcke bekommen ein synthetisches tool_result (`close_open_tool_uses`),
  damit die History für den nächsten Aufruf gültig bleibt. Die Tools laufen nicht.
- `errors_log.record(source="runner.refusal", severity="warning")` mit Modell, Iteration und Anzahl der Tools.
- Session-Status `abandoned`, dazu ein Error-Event mit `metadata.kind="refusal"` und einer klaren deutschen Meldung.
- Andere stop_reasons bleiben unverändert (leere Antwort weiterhin mit der allgemeinen Meldung).

### b) Frontend

- Die Fehlerleiste aus ChatPane wird als eigene Komponente `RunErrorBanner` ausgelagert und in
  ChatPane und auf der Buddy-Seite genutzt. Der Buddy bekommt damit auch den Button „Weitermachen“.
- `reload()` behält den Fehler, solange dieselbe Session nachgeladen wird. Er verschwindet
  beim nächsten Senden (wie bisher), beim Session-Wechsel und nach einem erfolgreichen Reload,
  wenn der Fehler vom Laden selbst kam (`errorKind="load"`).
  Als reine Funktion `errorAfterReload` in `_reloadMerge.ts`, damit sie testbar ist.

## Nicht Teil dieses PRs

- Fehler dauerhaft in der Session speichern (Reload der Seite, anderes Gerät): Task 71663ae3.

## Tests

- core: `tests/test_runner_refusal.py` (refusal mit nur thinking, mit Text und mit Tool; errors_log;
  tool_result für offene tool_use; end_turn und leere Antwort unverändert).
- frontend: `errorAfterReload` (vitest), `RunErrorBanner` per `renderToStaticMarkup`.
