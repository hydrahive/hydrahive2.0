# Feature Map: Compaction — Context-Window-Management

> **Modul:** `core/src/hydrahive/compaction/`  
> **Was:** Automatische Kontext-Kompression. Wenn Context-Window voll → Summary erstellen, alte Messages ausblenden.  
> **Warum:** LLMs haben begrenzte Context-Windows. Ohne Compaction: Fehler bei langen Sessions.  
> **Kernprinzip: Zero-Context-Loss** — keine Daten werden gelöscht, nur der Pointer verschoben.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `hooks.py` | `should_compact()` prüfen nach jeder Antwort. Trigger-Punkt im Runner. |
| `compactor.py` | Haupt-Compaction-Logik. `compact_session()` ausführen. |
| `summarize.py` | LLM-Call zur Summary-Erstellung. |
| `cut_point.py` | `find_cut_point()` — wo genau soll komprimiert werden? |
| `_chunking.py` | Nachrichten in sinnvolle Chunks für Summarization aufteilen |
| `_prompts.py` | System-Prompts für die Summarization |
| `redact.py` | Sensitive Daten aus Compaction-Summary herausfiltern |
| `serialize.py` | Messages in Text-Format für Summarization serialisieren |
| `tokens.py` | `context_window_for(model)` — Context-Window-Größe per Modell |
| `_storage.py` | Compaction-Block in DB speichern |

---

## Ablauf

```
Runner (nach jeder Antwort):
│
├── should_compact(session, agent_config)?
│   ├── Prüft: Token-Usage > compact_threshold_pct * context_window?
│   ├── Prüft: compact_max_turns erreicht?
│   └── Gibt True/False zurück
│
└── Falls True: compact_session(session_id, agent_config)
    │
    ├── History laden (alle Messages ab first_kept_entry_id)
    ├── find_cut_point() — letzte N Messages NICHT komprimieren (frischer Context)
    │
    ├── Zu kompaktorende Messages serialisieren (serialize.py)
    ├── Summary per LLM generieren (summarize.py)
    │   └── compact_model (oder fallback: llm_model)
    │
    ├── Compaction-Block in DB speichern (_storage.py)
    │   └── compaction_events.create(session_id, summary, new_first_kept_entry_id)
    │
    └── sessions.update(first_kept_entry_id=new_pointer)
        └── Ab jetzt: prepare_history() ignoriert alte Messages
```

---

## Zero-Context-Loss erklärt

```
Vorher:
  entry_id: 0  [user: "Wie geht's?"]      ← first_kept_entry_id = 0
  entry_id: 1  [assistant: "Gut!"]
  entry_id: 2  [user: "Was ist Python?"]
  ...
  entry_id: 50 [user: "Neue Frage"]        ← 50 Messages, Context voll

Compaction passiert:
  → Summary erstellt: "Wir haben über Python, Django, APIs gesprochen..."
  → first_kept_entry_id = 45 (letzte 5 Messages bleiben fresh)

Danach:
  entry_id: 0-44: VORHANDEN in DB, aber nicht im LLM-Context
  entry_id: 45+:  Werden an LLM gesendet
  compaction_block: "Zusammenfassung: Wir haben über..."

Was der LLM sieht:
  [System: Zusammenfassung von früher: ...]
  [user] entry 45
  [assistant] entry 46
  ...
```

---

## Konfigurationsparameter

| Parameter | Default | Beschreibung |
|---|---|---|
| `compact_threshold_pct` | 80 | Compaction bei X% des Context-Windows |
| `compact_max_turns` | None | Alternativ: nach N Turns komprimieren |
| `compact_model` | = llm_model | Modell für Summary-Generierung |
| `compact_tool_result_limit` | None | Tool-Results in Summarization kürzen |
| `compact_reserve_tokens` | None | Tokens für neue Antwort reservieren |

---

## Context-Window-Größen (tokens.py)

| Modell-Familie | Context-Window |
|---|---|
| claude-3.5-sonnet | 200.000 |
| claude-opus-4 | 200.000 |
| gpt-4o | 128.000 |
| gpt-4-turbo | 128.000 |
| deepseek-chat | 64.000 |
| (Fallback) | 100.000 |

---

## Wichtige Hinweise

- **Nie manuell `first_kept_entry_id` zurücksetzen** — das würde alten Context wieder sichtbar machen
- **Compaction ist teuer**: Ein extra LLM-Call pro Compaction
- **compact_model sollte günstig sein** wenn nicht der Haupt-Agent (z.B. Haiku statt Opus)
- **Summary ist immer sichtbar** im System-Prompt (als Summary-Block)

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): ruft `should_compact()` + `compact_session()` auf
- **→ DB** (`03-db.md`): `compaction_events`, `first_kept_entry_id` in sessions
- **→ LLM** (`12-llm.md`): `compact_model` muss ein gültiges Modell sein
