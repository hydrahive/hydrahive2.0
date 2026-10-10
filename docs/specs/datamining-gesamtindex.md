# Datamining-Gesamtindex: Volltext über alles + Hybrid-Suche

Task 75192a8e · Stand 10.10.2026 · Freigabe Till 10.10. · G1 umgesetzt

## 1. Ziel
„Kein Workflow mit Alzheimer“ (Till, 09.10.): Die Wortsuche muss **alle** Einträge durchsuchen, nicht nur ein Fenster der
neuesten. In den Kontext kommt trotzdem nur ein kleiner, gezielter Auszug (eigene Spec „Kontext-Bauer“, folgt).

## 2. Befund (gemessen 09./10.10., echte DB .2, nur lesend bzw. TEMP-Tabellen)
| | heute (`datamining_search`) | Gesamtindex (gemessen) |
|---|---|---|
| durchsucht | ganze Anfrage als **ein** ILIKE-Text | alle 572.614 Einträge, Wörter einzeln |
| Treffer@5, 10 echte Fragen | **0 %** | Wort 40 %, **Hybrid 60 %** (MRR 0,349) |
| Laufzeit | Median 1,8–3,9 s, bis 13–16 s (Pool-Timeout 10 s) | Median 63 ms, max 0,2 s |
| Agenten-Aufrufe ohne Treffer (30 Tage) | 29 % (59 % bei 4+ Wörtern) | – |

Weitere Befunde:
- **Wörter über Stückgrenzen:** Werkzeug-Ausgaben sind in 3.000er-Stücke geteilt; 49 % der Grenzen liegen mitten im Wort
  (Stichprobe 8.081 Grenzen) → je Stück gesucht findet man solche Wörter nicht. 24.514 Ergebnisse betroffen.
- **Wortformen:** `simple` vs. `german` gleich gut (40 % / 40 %), `simple` baut halb so lang (54 s vs. 107 s). Präfix-Suche
  (`wort:*`) bringt nichts.
- **Bauweise** (alle Daten):

| Variante | Aufbau | Platz | Wörter über Stückgrenzen |
|---|---|---|---|
| V1 Ausdrucks-Index direkt auf `events` (je Ereignis) | 77 s | GIN 235 MB | **fehlen** |
| **V2 eigene Tabelle `event_docs`**, nur `tsvector`, je Werkzeug-Ergebnis 1 Dokument | 80 s | Tabelle 272 MB + GIN 225 MB | **gefunden** |

  Pflege V2: 1.000 Dokumente neu berechnen + Upsert = 283 ms.

## 3. Lösung
### 3.1 Tabelle `event_docs` (V2)
```
doc_id      TEXT PRIMARY KEY   -- 'r:' || tool_use_id bei Werkzeug-Ergebnissen, sonst events.id
session_id, username, agent_id, project_id, created_at   -- für die Sicht (_mirror_scope.where braucht genau diese)
tsv         TSVECTOR           -- to_tsvector('simple', left(alle Stücke zusammen, 1.000.000))
```
- GIN-Index auf `tsv`; Index auf `(username, created_at)` und `(session_id)`.
- Zusätzlich Teil-Index `events(tool_use_id) WHERE tool_use_id IS NOT NULL` (additiv, 12 MB, 1,7 s): ohne ihn liest jede
  Aktualisierung die ganze `events`-Tabelle (gemessen 106–372 ms je Aufruf, Seq Scan), mit ihm 4 ms.
- **Kein** Text-Duplikat – Ausschnitte (`ts_headline`) werden nur für die Top-Treffer aus `events` gebaut.
- `events` bleibt unverändert (keine DDL auf der 8,9-GB-Tabelle).
- Anlage über `DDL_TABLES` (`CREATE … IF NOT EXISTS`), keine Spaltenänderung an bestehenden Tabellen.

### 3.2 Pflege
- **Beim Spiegeln:** nach jedem `INSERT INTO events` die betroffenen `doc_id`s neu berechnen (Upsert). Schreibpfade laut Code:
  `_mirror_writes`, `_mirror_fulltext_backfill`, `_datamining_rechunk` (DELETE+INSERT desselben Ergebnisses),
  Importe (`mirror_import_git/_shell/_logs/_sqlite`), `datamining.py` Ingest, `datamining_issues`.
  Eine gemeinsame Funktion `refresh_docs(conn, doc_ids)`, keine Kopien in jedem Pfad.
- **Nachholen:** idempotenter Lauf, der fehlende/veraltete Dokumente findet (`events.mirrored_at` neuer als Dokument) –
  nachts mit der Zahnfee (nach dem Volltext-Nachtrag) + Admin-Route `POST /api/datamining/index/sync`. Fehlen mindestens
  20.000 Dokumente (z. B. leerer Index, aber auch direkt nach dem ersten Start, wenn die Pflege beim Spiegeln schon
  neue Nachrichten eingetragen hat – Befund 10.10.) → ein Voll-Aufbau (gemessen auf Kopie: 116 s, 499.038 Dokumente),
  danach Runden à 2.000.
- **Abdeckungs-Zähler:** `GET /api/datamining/index/coverage` → `docs`, `missing`, `stale` (gemessen 0,8 s).
- **Platz** (gemessen auf Kopie, alle Daten): Tabelle 274 MB + ausgelagerte große tsvector 358 MB + Indizes 252 MB
  (GIN 201 MB) = rund **0,9 GB** zusätzlich zur 8,9-GB-Datenbank.

### 3.3 Suche
1. **Wörter:** Zerlegung wie im verworfenen Branch (`split_words`: ≥ 3 Zeichen, ohne Füllwörter, 6 längste).
   Abfrage = ODER aus `plainto_tsquery('simple', wort)` je Wort – **nie** selbst gebauter tsquery-Text (keine Syntax-
   Fehler, keine Injektion; Tokenisierung identisch zum Index, z. B. `update.sh`).
2. **Wortsuche:** `event_docs` mit GIN + Sicht (`_mirror_scope.where(alias='d')`) + Filter, Rang `ts_rank_cd`,
   Top-N Dokumente → Ausschnitt per `ts_headline` aus den zugehörigen `events`.
3. **Hybrid (Stufe 2):** Wortsuche + Bedeutungssuche (HNSW, `iterative_scan`) → **RRF** je Sitzung.
   Gewichtung erst festlegen, wenn mehr echte Fragen da sind (heute: echt +10 Pkt, synthetisch −10 Pkt).
4. **Werkzeuge:** `datamining_search` nutzt Stufe 1 (gleiches Antwortformat: Ereignisse mit snippet), Hybrid als eigener
   Schritt mit eigener Messung.

## 4. Etappen
- **G1** Tabelle + Pflege + Nachholen + Zähler (ohne Suche umzustellen). Messen: Abdeckung 100 %, Aufbauzeit.
- **G2** `datamining_search` auf `event_docs`. Abnahme Messrahmen + Agenten-Aufrufe 7 Tage danach.
- **G3** Hybrid (RRF), Gewichtung aus erweitertem Testsatz.
- **G4** Kontext-Bauer (eigene Spec).

## 5. Akzeptanz (G1 + G2)
- Jeder Eintrag mit Text hat ein Dokument (Zähler 0 offen); zweiter Nachhol-Lauf schreibt 0.
- Wort über Stückgrenze wird gefunden (Test + Stichprobe echte Daten).
- Messrahmen, echte Fragen: Wortsuche ≥ 40 % Treffer@5 (heute 0 %); Laufzeit max < 1 s über alles.
- Sicht unverändert: Mutanten wie bei #534 (Projekt, Stufe, Gruppen) greifen auch hier.
- Kein `mirror.init()` gegen die echte DB in Proben; DDL nur additiv.
- Tests + Mutanten ohne Bytecode-Cache; ruff; Dateien ≤ ~200 Zeilen.

## 6. Offen
- Mehr echte Fragen von Till für G3 (Gewichtung).
- Bestehende Secrets im Index (Task f328cb4b) – der Index übernimmt nur, was in `events` steht.
