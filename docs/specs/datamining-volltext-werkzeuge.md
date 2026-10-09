# Datamining: volle Werkzeug-Ausgaben in den Index (Teil B von Task 36caf245)

Stand 09.10.2026 · Grundsatz-Freigabe Till 09.10. („mach a und b“) · Details unten zur Freigabe

## 1. Befund (nur lesend, echte Daten .2)
- Das Datamining kürzt **nicht** selbst (`_mirror_explode`: Stücke à 3.000 Zeichen). Gekürzt wird vorher im Runner:
  `runner/dispatcher.to_tool_result_block` schneidet auf `tool_result_max_chars` des Agenten
  (12.000 / 50.000 / 8.000 / 4.000 Zeichen). Nur diese Fassung wird als Nachricht gespeichert und gespiegelt.
- Der **volle** Text steht in `sessions.db → tool_calls.result` (`db/tools.finish`).
- Betroffen: **2.305** Aufrufe (11.05.–09.10.2026), voller Text zusammen **466 MB**.
  - 32 Aufrufe über 1 MB, alle `shell_exec`, der größte 87 MB (Log-/Binärausgaben) → zusammen 362 MB.
  - Ohne diese: 104 MB. Je Aufruf auf 200.000 Zeichen begrenzt: 99 MB.
  - Werkzeuge: shell_exec 1.097, file_read 471, grep 319, fetch_url 155, task_list 112.
- **19** der vollen Texte enthalten Token-Muster (`ghp_`, `gho_`, `sk-ant-`, `github_pat_`, `sk-proj-`).

## 2. Lösung
1. **Nachtragen:** Für jeden gekürzten Aufruf (`result_truncated = 1`) den Rest des vollen Textes als
   zusätzliche Ereignisse in `events` schreiben – gleiche Sitzung, gleicher `tool_use_id`, `event_type = 'tool_result'`,
   in 3.000er-Stücken wie bisher. Markierung `chunk`-Felder fortlaufend; Kennung `source = 'full'` (neue Spalte
   oder im `id`-Schema, z. B. `{message_id}:{block}:full:{n}`), damit doppelte Läufe nichts doppelt schreiben.
2. **Laufend:** Neue gekürzte Aufrufe kommen auf demselben Weg nach (beim Spiegeln oder per Nachtrag-Lauf).
3. **Obergrenze je Aufruf:** 200.000 Zeichen (Vorschlag). Darüber nur Anfang + Ende, weil das fast immer
   Logs/Binärkram ist (die 87-MB-Ausgabe hilft niemandem beim Suchen).
4. **Secrets:** Vor dem Schreiben Token-Muster durch `[REDACTED]` ersetzen (gleiche Muster wie Task f328cb4b).
5. **Embedding:** Nur der Anfang je Aufruf wird eingebettet (die ersten Stücke bekommen ihr Embedding über den
   normalen Nachtrag); die Fortsetzungs-Stücke bekommen **kein** Embedding (`embedding_model = 'skip:full'`),
   sie sind nur für die Volltextsuche da. Spart Kosten und hält die Bedeutungssuche sauber.
6. **Kontext:** Unverändert – in den Kontext kommen weiterhin nur Ausschnitte (Spec Gesamtindex, folgt).
7. **Nichts ändert sich** an dem, was der Agent im Lauf sieht (seine Grenze bleibt), und an der Sicht
   (`_mirror_scope`), da gleiche Sitzung/Projekt/Nutzer.

## 3. Offene Entscheidungen (Till)
- Obergrenze je Aufruf: 200.000 Zeichen (≈ 99 MB gesamt) – oder höher/niedriger?
- Secrets: maskieren beim Nachtragen (Vorschlag) – die bestehenden 624 Fundstellen im Index räumt Task f328cb4b auf.

## 4. Akzeptanz
- Nach dem Nachtrag: für jeden gekürzten Aufruf ist der Text bis zur Obergrenze per Volltext auffindbar
  (Stichprobe: Wort, das nur im abgeschnittenen Teil steht, wird gefunden).
- Zweiter Lauf schreibt 0 neue Ereignisse (idempotent).
- Keine Token-Muster in den neuen Ereignissen.
- Keine neuen Embedding-Kosten für Fortsetzungs-Stücke.
- Tests + Mutanten ohne Bytecode-Cache.
