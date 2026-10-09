# Datamining: volle Werkzeug-Ausgaben in den Index (Teil B von Task 36caf245)

Stand 09.10.2026 · Freigabe Till 09.10. (Obergrenze 200.000 Zeichen, Secrets maskieren)

## 1. Befund (nur lesend, echte Daten .2)
- Das Datamining kürzt **nicht** selbst (`_mirror_explode`: Stücke à 3.000 Zeichen). Gekürzt wird vorher im Runner:
  `runner/dispatcher.to_tool_result_block` schneidet auf `tool_result_max_chars` des Agenten
  (12.000 / 50.000 / 8.000 / 4.000 Zeichen). Nur diese Fassung wird als Nachricht gespeichert und gespiegelt.
- Der **volle** Text steht in `sessions.db → tool_calls.result` (`db/tools.finish`).
- Betroffen: **2.305** Aufrufe (11.05.–09.10.2026), voller Text zusammen **466 MB**.
  - 32 Aufrufe über 1 MB, alle `shell_exec`, der größte 87 MB (Log-/Binärausgaben) → zusammen 362 MB.
  - Ohne diese: 104 MB. Je Aufruf auf 200.000 Zeichen begrenzt: 99 MB.
  - Werkzeuge: shell_exec 1.097, file_read 471, grep 319, fetch_url 155, task_list 112.
- 19 volle Texte enthalten Token-**Präfixe** (`ghp_`, `sk-ant-` …), geprüft: nur Präfixe/Kurzformen, **kein** echtes
  Secret laut `credentials.redaction.detect_secrets`. Geschwärzt wird trotzdem (gleiche SSOT-Muster).

## 2. Lösung
1. **Was nachgetragen wird:** `tool_calls.result` ist das JSON von `ToolResult`. Der Runner schneidet
   `ToolResult.to_llm()` ab – also wird dieselbe Fassung gebaut und der Teil **ab der Grenze** nachgetragen
   (gemessen: Index-Anfang == `to_llm()` bei 200/200 Stichproben, == Rohtext nur bei 3/200).
2. **Wohin:** zusätzliche `tool_result`-Ereignisse in `events`, gleiche Sitzung, Nachricht, Nutzer, Projekt, Zeit und
   `tool_use_id` wie das Original-Ergebnis; 3.000er-Stücke; ID `full:{tool_call_id}:{n}` (stabil →
   `ON CONFLICT DO NOTHING`, zweiter Lauf schreibt nichts). Nur wenn das Original im Index liegt und die Sitzung
   übereinstimmt (sonst übersprungen und gezählt).
3. **Obergrenze:** sichtbarer Teil + Rest ≤ 200.000 Zeichen; darüber vom Rest nur Anfang + Ende mit Hinweis
   „[… N Zeichen ausgelassen …]“.
4. **Secrets:** `credentials.redaction.redact_detected` (zentrale Muster, keine eigene Liste).
5. **Kein Embedding:** `embedding_model = 'skip:full'`. Embedding-Nachtrag, Zähler „pending“ und
   Embedding-Reset lassen `skip:%` in Ruhe.
6. **Wann:** nachts mit der Zahnfee (ohne LLM) + Admin-Route `POST /api/datamining/fulltext/backfill`.
7. **Unverändert:** was der Agent im Lauf sieht (seine Grenze bleibt), die Sicht (`_mirror_scope`), der Kontext
   (nur Ausschnitte, Spec Gesamtindex folgt).

Trockenlauf echte Daten 09.10. (nur lesend): 2.305 gekürzte Aufrufe, 2.294 mit Original im Index (11 ohne),
25.125 Stücke, 68,4 MB; Nahtstelle sichtbar + Rest == voller Text bei 150/150 Zufallsstichproben; 0 Secrets.

## 3. Akzeptanz
- Nach dem Nachtrag: für jeden gekürzten Aufruf ist der Text bis zur Obergrenze per Volltext auffindbar
  (Stichprobe: Wort, das nur im abgeschnittenen Teil steht, wird gefunden).
- Zweiter Lauf schreibt 0 neue Ereignisse (idempotent).
- Keine Token-Muster in den neuen Ereignissen.
- Keine neuen Embedding-Kosten für Fortsetzungs-Stücke.
- Tests + Mutanten ohne Bytecode-Cache.
