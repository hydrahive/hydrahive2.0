# Datamining-Spiegel: sauber herunterfahren + Lücken beim Start nachziehen

Task a11e9091 · 07.10.2026 · Befund Prod (nur lesend)

## Befund
Neustart 21:44:56 (Modul-Update): uvicorn bricht nach 20 s ab, danach dauert der lifespan-Shutdown noch **18 s**.
In der Zeit: 3× „PG-Mirror message … fehlgeschlagen: pool is closing“ und 3× „Embedding-Speichern fehlgeschlagen“.
- Ursache Dauer: `mirror.close()` ruft `_pool.close()`; asyncpg wartet dabei, bis alle ausgeliehenen Verbindungen
  zurück sind. Embedding-Aufgaben halten eine Verbindung erst NACH einem langsamen API-Aufruf (`aembed`), der
  Backfill (falls aktiv) ebenso; sie laufen weiter, weil sie nicht abgebrochen werden.
- Ursache Lücke: Das Backend lebt nach dem Abbruch noch (lifespan), Agenten-Läufe schreiben weiter Nachrichten →
  `schedule_message` startet neue Schreibaufgaben gegen einen schließenden Pool → „pool is closing“, keine
  Wiederholung („fire-and-forget, kein Retry“). Geprüft: die 3 Nachrichten (21:45:18/27/32, Sitzung 01a0e01b) sind
  per `datamining_search` nicht auffindbar, eine Nachricht von 21:38 schon. Embeddings holt der Backfill nach
  (sucht `embedding IS NULL`), Events nicht.

## Änderungen (eine Ursache = ein Commit)
1. **Sauber schließen** (`db/mirror.py`): Schreibaufgaben werden in einer Menge geführt (`_tasks`).
   `close()`: (a) keine neuen Aufträge mehr annehmen (`_closing`), (b) Backfill abbrechen, (c) laufende Aufgaben
   höchstens `CLOSE_WAIT_S` (5 s) abwarten, Rest abbrechen, (d) `pool.close()` mit Zeitgrenze, sonst
   `pool.terminate()`. Ergebnis: Shutdown-Anteil des Spiegels ≤ ~6 s.
2. **Lücke beim Start nachziehen** (`db/_mirror_catchup.py`): nach `init()` einmal im Hintergrund die Nachrichten
   der letzten `CATCHUP_HOURS` (6 h) aus SQLite lesen und fehlende Events einfügen (`ON CONFLICT DO NOTHING`,
   gleicher Weg wie `mirror_import_sqlite`, aber nur das Zeitfenster). Neu eingefügte Events bekommen Embeddings
   über den normalen Weg. Kosten: ein Zeitfenster, nicht die ganze DB.

## Tests (TDD)
- `close()` ohne Pool: nichts. Mit hängender Aufgabe (Future, die nie endet): `close()` endet nach ≤ CLOSE_WAIT_S +
  Puffer, Aufgabe ist abgebrochen, Pool geschlossen bzw. terminiert.
- Nach `close()` begonnen: `schedule_message` legt KEINE Aufgabe an.
- Pool-close hängt → `terminate()` wird gerufen.
- Nachziehen: liest nur das Zeitfenster (ältere Nachricht nicht), ruft das Einfügen mit den Events der neuen
  Nachrichten, Fehler werden geloggt, nicht geworfen; ohne Pool: nichts.

## Echt prüfen (hydratest)
Agent-Lauf, der während des Neustarts weiter schreibt → Neustart-Dauer messen (Ziel ≤ 30 s), danach die Nachricht
im Datamining finden (Nachziehen). Journal: kein „pool is closing“-Sturm.

## Nicht hier
Agent-Läufe beim Herunterfahren sauber beenden (sie schreiben nach dem Abbruch weiter) → gehört zu cb39123a bzw.
eigenem Task, falls nötig.
