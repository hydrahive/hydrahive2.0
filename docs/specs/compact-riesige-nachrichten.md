# Compact bei riesigen Einzelnachrichten

Task 5406d099. Befund bei einem externen Nutzer (Berkan, 27.10.2026): In einem Projekt-Chat mit 2,6 Mio. Tokens
scheiterte jedes Compact (automatisch und von Hand) mit „prompt is too long: 6.043.166 tokens > 1.000.000“. Der Chat
wuchs weiter, das nächste Compact scheiterte wieder. Eine Endlosschleife.

## Ursache

1. **`serialize.py`** kürzte nur Tool-Ergebnisse. Bilder und PDFs (base64), lange eingefügte Texte, Denk-Blöcke und
   unbekannte Blöcke (z. B. `codex_reasoning`) gingen per `json.dumps` ungekürzt in die Zusammenfassung.
2. **`_chunking.py`** schnitt nur an Zeilen, die mit `[Rolle]:` beginnen, also zwischen Nachrichten. Eine einzelne
   Nachricht, die größer war als ein Stück, blieb ein Stück. Nachgestellt:
   - eine Nachricht mit 300.000 Zeilen ergab 8,66 Mio. Tokens in einem Stück;
   - ein 8-MB-Einzeiler ergab 6,67 Mio. Tokens.
3. Vor dem Aufruf fehlte eine Prüfung. Der zu große Prompt ging trotzdem an das Modell und kostete Geld.

Auf dem Hauptserver gab es solche Fehler bisher nicht, das Risiko besteht aber genauso. Gefunden: eine Nachricht mit
einem Bild von 2,78 MB, die 2,3 Mio. „Tokens“ in einem Stück ergibt.

## Änderung

- **serialize:**
  - Bilder werden zu `[Bild: image/jpeg, 2,7 MB]` bzw. `[Bild: <url>]`.
  - Dokumente werden zu `[Dokument: <titel>, application/pdf, 2,7 MB]`.
  - Das gilt auch innerhalb von Tool-Ergebnissen und beim Assistenten.
- **Lange Texte** (Nutzer, Assistent, Denken, System, frühere Zusammenfassung) werden je Block auf `TEXT_BLOCK_LIMIT` =
  60.000 Zeichen gekürzt, mit dem Hinweis `…[gekürzt: N Zeichen]`. Normale Nachrichten bleiben unverändert.
- **Unbekannte Blöcke:**
  - Beim Assistenten werden sie weggelassen. Das sind interne bzw. verschlüsselte Denk-Daten ohne Wert für die
    Zusammenfassung.
  - Beim Nutzer wird `json.dumps` auf 2.000 Zeichen gekürzt.
- **Teilen in Stücke:** Ein Stück über der Grenze wird zusätzlich an Zeilen geteilt und eine zu lange Zeile mitten in
  der Zeile. Jedes Stück liegt damit garantiert unter der Grenze. Es geht nichts verloren, die Reihenfolge bleibt.
- **Letzte Sicherung:** `_single_summarize` und der Merge schätzen den Prompt vor dem Aufruf (dichte Schätzung). Ist
  er größer als das Fenster, wird nichts gesendet, sondern `SummaryTooLarge` geworfen. Das Ereignis landet wie jeder
  Compact-Fehler im Log (`compaction_events.error`).
- Eine sehr große frühere Zusammenfassung wird beim ersten Stück mitgerechnet.

## Für bestehende Chats

Nach dem Update klappt das nächste Compact in einem festhängenden Chat wieder. Die Bilder und PDFs bleiben in der
Unterhaltung erhalten. Nur die Zusammenfassung nennt sie, statt sie mitzuschicken.

## Abnahme

Berkan klickt nach dem Update im festhängenden Projekt-Chat auf „Compact“ (oder schreibt weiter und wartet auf das
automatische Compact). Erwartet wird: kein „prompt is too long“, der Token-Stand sinkt deutlich.
