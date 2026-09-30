# Dashboard: „Heute“ und „7 Tage“ nach Ereigniszeit, deutscher Tag, Dollar

Task a1b95d3b. Entscheidungen von Till am 30.09.2026: „heute“ nach deutscher Zeit, Kosten in Dollar.

## Problem

`/api/analytics/overview` liest `today`, `last_7d` und die Top-5 aus der View `session_metrics` mit `WHERE created_at >= Grenze`. `created_at` ist dort der **Session-Beginn**. Alles, was heute in einer älteren Session passiert, fehlt.

Belegt am 30.09.2026 (lesend):

| | Kachel | tatsächlich |
|---|---|---|
| Kosten heute | 0,03 $ | 223,06 $ (782 LLM-Aufrufe) |
| Fehler heute | 0 | 25 Tool-Fehler |
| Fehler 29.09. | 0 | 30 |

Dazu:
- Der Tag beginnt um UTC-Mitternacht (`today_start_iso`), in Deutschland also um 01:00 bzw. 02:00.
- Kosten sind Dollar-Preise (`llm/_pricing.py`, 1 $ = 100.000 `cost_micros`), die Oberfläche zeigt aber „€“ an (Dashboard und Session-Analyse), ohne umzurechnen.

## Lösung

### 1. Tagesgrenze nach deutscher Zeit

`today_start_iso()` liefert Mitternacht in `Europe/Berlin`, umgerechnet nach UTC im Format `YYYY-MM-DDTHH:MM:SS+00:00`. Alle Ereignis-Zeitstempel liegen in UTC (`…+00:00`, bei alten `messages` auch `…Z`). Ein Textvergleich gegen diese Grenze ist für beide Formate korrekt.

Die „7 Tage“ beginnen 7 Tage **vor der deutschen Mitternacht von heute**, ebenfalls nach UTC umgerechnet (`week_start_iso()`). Sommer- und Winterzeit werden durch `zoneinfo` richtig behandelt.

Betrifft `analytics.py` (overview) und `dashboard.py` (`tokens_today`, `tool_calls_today`). Diese zwei zählen schon nach Ereigniszeit, nur mit der falschen Grenze.

### 2. Summen nach Ereigniszeit

Neues Modul `db/usage_window.py` mit `totals(conn, since, username)`. Es summiert direkt aus den Ereignistabellen, gefiltert nach deren `created_at`:

| Feld | Quelle |
|---|---|
| input/output/cache_read/cache_creation_tokens, cost_micros, llm_calls | `llm_calls` |
| tool_calls, tool_errors | `tool_calls` (status) |
| compactions | `compaction_events` |
| errors | `errors_log` ohne Tool-Abstürze (`.crash`), die stehen schon in `tool_errors` |
| sessions | Anzahl verschiedener `session_id` in `llm_calls` im Zeitraum |

Filter „nur eigene“: `user_id` der Ereignistabelle. Geprüft: seit 01.09. ist `user_id` in allen vier Tabellen gesetzt und stimmt immer mit dem Session-Besitzer überein.

`today` und `last_7d` kommen aus `totals()`. Die Korrektur `crash_count` aus #484 entfällt, weil `errors` die Abstürze gar nicht erst zählt. `crash_count` hat keine anderen Nutzer und wird mit seinem Test entfernt. `CRASH_SOURCES` bleibt.

### 3. Top-5 teuerste Sessions

Nach den Kosten **im Zeitraum** (`SUM(llm_calls.cost_micros)` der letzten 7 Tage je Session), nicht nach den Gesamtkosten von Sessions, die im Zeitraum begonnen haben. Weitere Spalten (Tokens, Aufrufe, Fehler) ebenfalls für den Zeitraum.

### 4. Dollar statt Euro

- Dashboard (`_TokenAuditCard.tsx` `formatCents`) und Session-Analyse (`SessionDetailPage.tsx` `formatCost`) zeigen `$` bzw. `¢`. Die Rechnung bleibt, nur das Zeichen ändert sich.
- Beide Funktionen werden zu **einer** gemeinsamen `formatUsd()` in `frontend/src/features/dashboard/_format.ts` zusammengeführt, mit Tests.
- Gespeicherte Werte bleiben unverändert.

## Nicht in dieser Änderung

- Die View `session_metrics` selbst bleibt (Session-Analyse nutzt sie pro Session, dort ist Session-Beginn egal).
- Keine Währungsumrechnung.
- OpenRouter-Guthaben im Projekt-Cockpit bleibt wie es ist (schon `$`).
- Keine Migration, keine Datenänderung.

## Akzeptanzkriterien

1. Eine Aktivität heute in einer Session von gestern zählt in „heute“ (Tokens, Kosten, LLM-Aufrufe, Tool-Fehler, Compactions, Fehler).
2. Eine Aktivität von gestern 23:30 deutscher Zeit zählt nicht zu „heute“, eine von heute 00:30 deutscher Zeit schon, im Sommer und im Winter.
3. Ein Tool-Absturz zählt in „Heute Fehler“ genau einmal.
4. Nicht-Admins sehen nur eigene Ereignisse, Admins alle.
5. Top-5 sortiert nach Kosten im Zeitraum.
6. Oberfläche zeigt `$`, nirgends mehr `€` für LLM-Kosten.
7. Live-Rundlauf: Kachel „Heute Kosten“ stimmt mit `SUM(cost_micros)` aus `llm_calls` ab deutscher Mitternacht überein.
