# Compaction

> Lange Sessions schrumpfen kontrolliert ohne Geschichte zu verlieren —
> via append-only-Pointer in den Messages-Tabellen. Architektur-Inspiration:
> OpenClaw.

## Kernidee — `firstKeptEntryId`

Statt Messages aus der Historie zu löschen, wird ein **Pointer** in
`session_state` gepflegt: `firstKeptEntryId` markiert ab welcher message-id
die "frische" History anfängt. Alles davor:
- bleibt in der DB erhalten (Historie + Audit-Trail)
- wird als ein synthetisches `Summary`-Message dem LLM präsentiert
- ist im Frontend als "ältere Nachrichten" einklappbar verfügbar

```
DB:    [m1, m2, m3, m4, m5, m6, m7, m8, ...]  (alle erhalten)
                       ▲
              firstKeptEntryId = m4

LLM-View (via list_for_llm):
       [SUMMARY{summary of m1-m3}, m4, m5, m6, m7, m8]
```

Append-only: kein DELETE, nur Pointer-Update. Jede Compaction-Pass kann
fehlerfrei wiederholt werden, bei Crash ist der State konsistent.

## Trigger

```
should_compact(messages, model)
  ├─ context-Window des Modells bestimmen (compaction/tokens.context_window_for)
  ├─ used_tokens schätzen (Anthropic count_tokens API oder estimate_dense_text)
  ├─ usable = window - reserve_tokens (default 16384, per-agent overridebar)
  ├─ trigger wenn used > usable * (compact_threshold_pct / 100)
  └─ default threshold: 100% — also erst wenn das Limit erreicht wäre
```

Per-Agent-Konfiguration (alle in `agents/_defaults.py`):

| Feld | Default | Effekt |
|---|---|---|
| `compact_model` | `""` (= main llm_model) | Override für Compact-LLM, z.B. claude-haiku |
| `compact_tool_result_limit` | 2000 | wie weit Tool-Results in der serialisierten History gekürzt werden |
| `compact_reserve_tokens` | 16384 | Reserve für Summary-Antwort + neue Iteration |
| `compact_threshold_pct` | 100 | wann triggert auto-compact |
| `tool_result_max_chars` | 12000 | Live-Truncation vor LLM-Call (verschieden von compact_tool_result_limit!) |
| `cache_ttl` | `1h` | Anthropic Prompt-Cache TTL für stabilen System-Prompt |

## Pass-Ablauf — `compact_session`

```
compact_session(session_id, model, ...)
  ├─ load messages
  ├─ find_cut_point(messages, keep_recent_tokens)         compaction/cut_point.py
  │   → wo schneiden? Tool-Use-Paare nicht mittendrin trennen
  │   → keep_recent_tokens (default ~6k) bleibt frisch
  ├─ serialize older messages                              compaction/serialize.py
  │   → strip secrets via redact.py
  │   → cut tool_results to compact_tool_result_limit
  ├─ summarize via LLM                                     compaction/summarize.py
  │   → prompt aus _prompts.py (DE)
  │   → wenn Older > 1 Window: hierarchisch mergen
  │     (chunks → mid-summaries → final summary, _merge_summaries)
  ├─ save Summary in session_state                         _storage.py
  └─ update firstKeptEntryId
```

### Hierarchisches Merging

Wenn die alte Historie selbst zu groß für ein Summary-Call ist:

1. Chunks der älteren Messages → individuelle Mid-Summaries
2. Mid-Summaries werden zusammengeführt zu Final-Summary
3. Rekursion bis Final-Summary ins Window passt

Implementiert in `summarize._merge_summaries`. Verhindert Crashes bei
Sessions die multi-window große Historie haben.

## Secret-Redaction

`compaction/redact.py` läuft vor Summary-Call und ersetzt:
- `password=...`, `token=...`, `api_key=...` → `[REDACTED]`
- `Authorization: Bearer xxx` → `[REDACTED]`
- bekannte Provider-Key-Prefixes (`sk-ant-`, `hhk_`, `xoxb-`, `ghp_`)

Wichtig weil sonst Credentials im Summary persistiert werden würden.

## File-Tracking

`compaction/_chunking.py` extrahiert `files_affected` aus `file_read/write/patch`
Tool-Calls in den älteren Messages. Diese Info wird im Summary aufgelistet —
das LLM weiß dann nach Compact: "in dieser Session wurden src/foo.py und
tests/test_foo.py angefasst".

## Plugin-Hooks

`compaction/hooks.py` definiert:
- `pre_compact(session_id)` — vor Cut/Summary
- `post_compact(session_id, summary, files_affected)` — nach Persistierung

Plugins registrieren sich via `register_pre_compact_hook` / `register_post_compact_hook`.

## Live-Truncation (kein Compact-Trigger)

Unabhängig vom Compaction-Schwellenwert wird **jedes einzelne Tool-Result**
auf `tool_result_max_chars` (Default 12000 Zeichen) gekürzt bevor es in den
LLM-Context geht (`runner/dispatcher.py:to_tool_result_block`). Das verhindert
dass ein einzelner riesiger Tool-Output (z.B. 52k JSON von `fetch_url`) eine
Iteration "tötet" (Anthropic 400 "input too long").

Das ist unabhängig von `compact_tool_result_limit`, das beim Serialisieren
der älteren Historie greift (kann aggressiver sein, z.B. 500 statt 12000).

## Wichtige Dateien

| Datei | Verantwortung |
|---|---|
| `compaction/__init__.py` | Public-Facade |
| `compaction/compactor.py` | `compact_session`, `should_compact` |
| `compaction/cut_point.py` | Wo schneiden — Tool-Use-Paare schützen |
| `compaction/summarize.py` | LLM-Call + hierarchisches Merging |
| `compaction/_prompts.py` | DE-Summary-Prompts |
| `compaction/_chunking.py` | Splitting older messages, File-Tracking |
| `compaction/serialize.py` | Messages → Text für Summary-Input |
| `compaction/redact.py` | Secret-Redaction vor Summary |
| `compaction/tokens.py` | `context_window_for(model)`, Token-Schätzung |
| `compaction/_storage.py` | session_state Lese/Write für firstKeptEntryId |
| `compaction/hooks.py` | Plugin-Hook-System |
| `runner/dispatcher.py` | Live-Truncation pro Tool-Result |

## Tests

- `test_compaction.py` (28) — Tokens-Estimation, find_cut_point, should_compact
