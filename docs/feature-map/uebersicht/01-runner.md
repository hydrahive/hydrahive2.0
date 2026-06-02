# Feature Map: Runner — LLM-Loop / Agent Execution Engine

> **Modul:** `core/src/hydrahive/runner/`  
> **Was:** Die Kernmaschine. Nimmt User-Input, baut LLM-Request, führt Tools aus, liefert Antwort.  
> **Warum:** Zentrales Orchestrierungsmodul — ohne Runner kein Agenten-Verhalten.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `runner.py` | **Haupt-Loop.** `run()` ist der Entry-Point. Orchestriert alles. |
| `_runner_iter.py` | Eine Iteration: `stream_llm_call()`, `prepare_history()` |
| `_runner_tools.py` | Tool-Verarbeitung nach LLM-Call: `process_tool_uses()` |
| `_runner_helpers.py` | Hilfsfunktionen: `close_open_tool_uses()` |
| `dispatcher.py` | **Tool-Dispatch.** `execute_tool()` — leitet an REGISTRY / MCP / Plugin-Bridge weiter |
| `_call.py` | **LLM-Call-Abstraction.** Streaming-Versuch + Non-Streaming-Fallback + Failover |
| `llm_bridge.py` | Non-Streaming LiteLLM-Call mit Caching-Hints |
| `llm_bridge_stream.py` | Streaming LiteLLM-Call. `StreamingNotSupported` wenn Modell kein Stream kann |
| `_llm_bridge_backends.py` | LiteLLM-Backend-Wrappers für verschiedene Provider |
| `_codex_provider.py` | OpenAI Codex Predicted Outputs (spezieller Pfad) |
| `_failover.py` | `should_failover()` — entscheidet ob Quota/Overload → nächstes Modell |
| `system_prompt.py` | `compose()` — baut den finalen System-Prompt (stable + volatile + skills + emote-hint) |
| `_emote_hint.py` | Fügt Hydra-Emote-Verwendungshinweis in System-Prompt ein |
| `context.py` | `to_anthropic_messages()`, `extract_tool_uses()`, `heal_orphan_tool_uses()` |
| `events.py` | Event-Dataclasses: `Done`, `Error`, `IterationStart`, `MessageStart`, `TextBlock`, `TextDelta` |
| `tool_confirmation.py` | Per-Tool Bestätigungs-UI (Tool-Confirm-Banner im Frontend) |
| `_media.py` | `extract_media()` — extrahiert Medien-Referenzen aus Tool-Results |

---

## Ablauf einer Anfrage (detailliert)

```
runner.run(session_id, user_input)
│
├── Session laden (sessions_db.get)
├── Agent-Config laden (agent_config.get)
├── Workspace sicherstellen (ensure_workspace)
├── ToolContext erstellen
├── session_start() Event
│
├── System-Prompt bauen (compose_system_prompts)
│   ├── Stable-Block: Persona, Regeln, Features
│   ├── Volatile-Block: Datum/Zeit, dynamische Infos
│   ├── Summary-Block: Compaction-Zusammenfassung (wenn vorhanden)
│   └── Skills: aktive Skill-Markdown-Blöcke
│
├── Tool-Schemas sammeln
│   ├── schemas_for(local_tools) — aus REGISTRY
│   ├── mcp_bridge.schemas_for_servers() — MCP-Server-Tools
│   └── plugin_bridge.schemas_for() — Plugin-Tools
│
├── user_input in DB speichern (messages_db.append)
│
└── Loop (max_iterations):
    ├── prepare_history() — History aus DB, mit Compaction-Truncation
    ├── call_with_stream_or_fallback()
    │   ├── Streaming versuchen (primary model)
    │   │   └── Bei Fehler: auf Non-Streaming fallen
    │   └── Non-Streaming mit Modell-Failover
    │
    ├── Events streamen (MessageStart, TextDelta, TextBlock, ...)
    ├── process_tool_uses() — alle Tool-Calls in diesem Turn
    │   └── execute_tool() pro Tool-Call
    │       ├── tools_db.create() — Persistenz
    │       ├── REGISTRY-Lookup
    │       ├── MCP-Bridge (wenn mcp__-Prefix)
    │       ├── Plugin-Bridge (wenn plugin__-Prefix)
    │       └── Ergebnis + Duration speichern
    │
    ├── Token-Kosten berechnen + in DB speichern
    ├── Compaction-Check (should_compact?)
    │   └── compact_session() wenn nötig
    │
    └── Bei stop_reason == "end_turn": Loop verlassen → Done-Event
```

---

## Wichtige Konzepte

### Tool-Execution-Sicherheit
- Jeder Tool-Call wird in `tools_db` persistiert — auch fehlerhafte
- Nicht erlaubte Tools → `ToolResult.fail()` (LLM bekommt Feedback, Runner crasht nicht)
- Alle Exceptions werden gefangen und als `Tool-Crash: ExceptionType: ...` zurückgegeben

### Streaming vs. Non-Streaming
- **Streaming** wird nur auf dem primären Modell versucht
- Wenn Stream mittendrin fehlschlägt: schlechte Erfahrung für User (schon Tokens gesehen)
- Daher: Stream-Fehler → kompletter Neustart auf Non-Streaming
- Non-Streaming unterstützt Failover auf alternative Modelle

### Loop-Detection
- `LOOP_DETECTION_WINDOW = 3` — wenn dieselben Tool-Calls 3× hintereinander: Abbruch
- Verhindert endlose Tool-Schleifen

### Reasoning-Effort
- Parameter `reasoning_effort` (low/medium/high) wird an LLM durchgereicht
- Frontend-Pill steuert das, Runner leitet weiter
- Nur bei Modellen die es unterstützen (Claude 3.5+, o1/o3)

### Modell-Failover
- `_failover.should_failover(error)` prüft ob Fehler failover-würdig ist (Quota, Overload)
- Liste der Fallback-Modelle aus Agent-Config (`fallback_models`)
- Non-failover-Fehler (z.B. Auth-Error) werden sofort raised

---

## Konfigurierbare Agent-Parameter (Runner-relevant)

| Parameter | Default | Beschreibung |
|---|---|---|
| `max_iterations` | 15 | Max Tool-Runden pro Request |
| `llm_model` | — | Primäres Modell |
| `fallback_models` | [] | Failover-Modelle |
| `compact_model` | = llm_model | Modell für Compaction-Summaries |
| `compact_threshold_pct` | 80 | Compaction ab X% des Context-Windows |
| `compact_max_turns` | None | Alternativ: Compaction nach N Turns |
| `compact_tool_result_limit` | None | Tool-Results in Compaction kürzen |
| `compact_reserve_tokens` | None | Tokens für neuen Output reservieren |
| `tool_result_max_chars` | 0 (unbegrenzt) | Tool-Results auf N Zeichen kürzen |
| `cache_ttl` | "1h" | Prompt-Cache-TTL (Anthropic-Feature) |
| `reasoning_effort` | None | Reasoning-Budget (low/medium/high) |
| `tools` | [] | Liste erlaubter Tool-Namen |
| `mcp_servers` | [] | Liste MCP-Server-IDs |

---

## Import-Regeln (CRITICAL)

```python
# ERLAUBT im Runner:
from hydrahive.tools import ...
from hydrahive.db import ...
from hydrahive.llm import ...
from hydrahive.compaction import ...
from hydrahive.agents import config as agent_config
from hydrahive.mcp import tool_bridge as mcp_bridge
from hydrahive.plugins import tool_bridge as plugin_bridge

# VERBOTEN:
from hydrahive.api import ...   # Zirkulärer Import!
```

---

## Verwandte Subsysteme

- **→ Tools** (`02-tools.md`): alle Tool-Implementierungen die der Dispatcher aufruft
- **→ Compaction** (`06-compaction.md`): wird nach jeder Iteration geprüft/ausgeführt
- **→ DB** (`03-db.md`): messages, tools, llm_calls, sessions werden hier geschrieben
- **→ LLM** (`12-llm.md`): Provider-Catalog, Modell-Auswahl
- **→ MCP** (`13-mcp.md`): MCP-Bridge wird in Dispatcher genutzt
- **→ Plugins** (`10-plugins.md`): Plugin-Bridge wird in Dispatcher genutzt
- **→ Streaming** (`22-streaming.md`): SSE-Events werden vom Runner-Output gespeist
