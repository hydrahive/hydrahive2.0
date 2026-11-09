# Compaction-Zuverlässigkeit: Fallback, Cooldown und Zeitbudget

## Ausgangslage

Read-only-Telemetrie am 09.11.2026: 64 Compaction-Events in 30 Tagen, davon 52 erfolgreich und 12 fehlerhaft. Die Fehler bestanden aus drei nicht erreichbaren Ollama-Aufrufen und neun Anthropic-429-Aufrufen derselben Session. Nach einem Fehler wurde ohne Cooldown beim nächsten Runner-Durchlauf erneut kompaktifiziert. Erfolgreiche Läufe dauerten p50 302,9 s, p90 661,5 s und maximal 1.025,4 s.

Ein aktueller Lauf erzeugte sieben sequenzielle Chunks. `_hard_split` legte nach einem vollen Stück den kleinen Rest einer überlangen Zeile sofort als eigenen Chunk ab, statt ihn mit folgenden Zeilen zu packen. Dadurch entstanden abwechselnd sehr große und nur 2–4 kB kleine Modellaufrufe.

## Änderung

1. `_hard_split` packt den Rest einer überlangen Zeile zusammen mit folgenden Zeilen, solange das Chunk-Budget reicht. Reihenfolge und Inhalt bleiben bytegenau erhalten.
2. Compaction erhält ausschließlich die bereits am Agenten konfigurierten `fallback_models`. Bei Rate-Limit-, Auth-, Kapazitäts- oder Verbindungsfehlern wird sequenziell auf das nächste Modell gewechselt.
3. Nach einem fehlgeschlagenen automatischen Lauf gilt pro Session fünf Minuten Cooldown. Manuelle Compaction bleibt möglich.
4. Ein kompletter Compaction-Lauf erhält ein hartes Zeitbudget von 900 Sekunden. Timeout oder externe Cancellation persistieren als Fehlerereignis; bis zum Persist-Schritt bleibt die bestehende Historie unverändert.
5. Chunk-Aufrufe bleiben bewusst sequenziell. Keine zusätzliche Parallelität und keine Änderung an AgentLink-, Delegations- oder Subagent-Timeouts/-Statusübergängen.

## Subagent-Schutz

- Es werden keine neuen Modelle erfunden; verwendet werden nur `compact_model` und die vorhandene `fallback_models`-Liste des Agenten.
- Compaction-Fehler und Cooldown behalten das bestehende Verhalten: Der Runner arbeitet mit der unveränderten Historie weiter und markiert keine Delegation als fehlgeschlagen.
- Eine äußere AgentLink-Cancellation wird nicht geschluckt. Sie propagiert weiter, während Compaction-Telemetrie den Abbruch dokumentiert.
- Kein Parallelisieren von Chunk-Aufrufen, damit Rate-Limits und laufende Spezialisten nicht zusätzlich belastet werden.

## Akzeptanzkriterien

1. Chunking verliert oder vertauscht kein Zeichen und erzeugt keine vermeidbaren Mini-Restchunks.
2. Ein retrybarer Primärmodellfehler nutzt genau die konfigurierten Fallbackmodelle in Reihenfolge.
3. Nicht-retrybare Fehler wechseln das Modell nicht.
4. Ein Fehler blockiert weitere automatische Versuche derselben Session für fünf Minuten; danach ist ein neuer Versuch möglich.
5. Manuelle Compaction wird vom Auto-Cooldown nicht blockiert.
6. Nach 900 Sekunden endet der Lauf deterministisch; kein Summary-Pointer wird halb geschrieben.
7. Timeout/Cancellation erscheint als fehlerhaftes `compaction_events`-Ereignis.
8. Bestehende Runner-, Compaction-, AgentLink- und Delegationstests bleiben grün.

## Nachtrag Review 09.11.2026

Drei Fehler der ersten Fassung wurden belegt und korrigiert:

1. **Fallback griff im Hauptfall nicht.** Die Stücke wurden für das Fenster des Primärmodells geschnitten (Opus 1M).
   Der Fallback (Luna 372k) verwarf sie mit `SummaryTooLarge`, ohne je aufgerufen zu werden. Jetzt wird pro Modell
   komplett neu zerlegt. Die Tests nutzen echte Modell-IDs und Fenster; erfundene Namen hatten den Fehler verdeckt.
2. **900-s-Gesamtlimit war zu knapp.** Die längste erfolgreiche Compaction dauerte 1.025 s. Ein Limit darunter
   bricht ab und lässt den Lauf nach dem Cooldown erneut bezahlen. Standard ist jetzt kein Gesamtlimit; gegen
   Retry-Stürme wirkt der Auto-Cooldown.
3. **Nebenwirkung im Chat.** Die Verbindungsfehler-Regeln standen im gemeinsamen `runner/_failover.py` und ließen
   damit auch den normalen Chat das Modell wechseln – entgegen #205. Sie liegen jetzt nur in `compaction/_llm.py`.

Bekannte Grenze: Schlägt ein Modell mitten in einer langen Compaction fehl, beginnt der Fallback von vorn. Teilergebnisse
werden nicht übernommen, weil sie für ein anderes Fenster zerlegt waren.
