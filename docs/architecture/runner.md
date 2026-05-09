# Runner / Tool-Loop

> Wie eine User-Frage zu einer Stream-Antwort wird, durch beliebig viele
> Tool-Iterationen.

## Eingang

Jeder User-Input löst einen Runner-Lauf aus, getriggert über die Chat-API:

```
POST /api/sessions/<id>/messages
   → runner.run_session(session_id, user_input, ...) — async generator
   → yields Events (TextDelta, ToolCall, ToolResult, IterationStart, Done, Error)
```

Events gehen via SSE-Stream zurück zum Frontend.

## Eine Iteration (= ein LLM-Roundtrip)

```
load agent + session                        runner.py
load + compact history if needed           _runner_iter.prepare_history
build system prompt                         _runner_iter.build_system_prompts
  + base prompt (from agents/_prompt.py)
  + skills block
  + memory_context (Crystals + Lessons)    agents/_context_injection.py
  + longterm_memory tools (if enabled)     _runner_setup.inject_longterm_memory
  + volatile system (per-message dynamic)
                  │
                  ▼
stream_llm_call (yields events live)        _runner_iter.stream_llm_call
  → call_with_stream_or_fallback           _call.py
    → stream path: stream_with_tools        llm_bridge_stream + _stream_providers
      → message_start, text_delta..., message_stop {usage, blocks, stop_reason}
    → fallback (on Stream-Error / unsupported):
        for model in [primary, *fallbacks]:
          call_with_tools                   llm_bridge.py → _llm_bridge_backends.py
            → anthropic_call / minimax_anthropic_call /
              litellm_call / codex_call
            → returns (blocks, stop_reason, usage)        ← B5-Fix Token-Counts
                  │
                  ▼
IterationResult {blocks, stop_reason, model, usage}
                  │
                  ▼
record_observation per tool_use block       tools/_observations.py
                  │
                  ▼
process_tool_uses                            _runner_tools.py
  → dispatch jeder tool_use → tool result
  → live truncation (tool_result_max_chars) before adding to history
  → Tool-Confirmation-Future (siehe tool_confirmation.py) wenn agent.require_tool_confirm
                  │
                  ▼
heal_orphan_tool_uses                        runner/context.py
  (verhindert 400 'multiple tool_result blocks' bei langen Sessions)
                  │
                  ▼
loop until stop_reason == 'end_turn'
or max_iterations reached
or all tools fail
                  │
                  ▼
yield Done event
```

## Stop-Reason-Behandlung

Aus Anthropic-API:

| Stop-Reason | Bedeutung | Runner-Reaktion |
|---|---|---|
| `end_turn` | Modell ist fertig | `Done`-Event, Loop-Exit |
| `tool_use` | Modell will Tool aufrufen | Process tools, nächste Iter |
| `max_tokens` | Modell wurde abgeschnitten | Warning, Loop-Exit (Tool-Use kann broken sein) |
| `stop_sequence` | Manueller Stop | Loop-Exit |

## Token-Counts (Quelle der Wahrheit)

**Streaming-Path (Normal-Case):** `_stream_providers.py:74-79` extrahiert aus
`message_stop`-Event (Anthropic-SDK liefert `usage` im Stream-Final).

**Fallback-Path (B5-Fix, Commit `a655deb`):** alle 3 Backends + `codex_call`
geben `(blocks, stop_reason, usage)` zurück. `_call.py` reicht das durch
an `CallResult`. Davor: alle 4 Counts auf 0 in metadata.

Helper: `runner/_token_usage.py`:
- `usage_dict(usage)` für Anthropic-Response-Format
- `usage_from_litellm(resp)` für OpenAI-kompatibles Format

## Streaming-Provider-Map

| Modell-Pattern | Provider | Stream-Quelle |
|---|---|---|
| `claude-*` | Anthropic SDK + `resolve_anthropic_token` (OAuth oder API-Key) | `_stream_providers.anthropic_stream` |
| `minimax/*` | Direkter SDK-Call gegen `api.minimax.io/anthropic` | `_stream_providers` |
| `openai-codex/*` | ChatGPT Plus/Pro über `chatgpt.com/backend-api/codex/responses` | `_codex_provider.codex_stream` |
| Alle anderen | LiteLLM (OpenAI, NVIDIA NIM, Groq, Mistral, Gemini, OpenRouter, …) | LiteLLM-Streaming |

Modell-Auflösung in `runner/llm_bridge.py:call_with_tools` (Switch nach
`is_minimax_model` / `is_claude` / `target.startswith("openai-codex/")`).

## Tool-Loop-Sicherungen

### `heal_orphan_tool_uses` (Commit `ac87d17`)

Wenn die History tool_use-Blöcke ohne korrespondierendes tool_result enthält
(z.B. nach Crash mitten in der Iteration), würde der nächste Anthropic-Call
mit 400 "multiple tool_result blocks" fehlschlagen. `heal_orphan_tool_uses`
schließt offene tool_uses mit Stub-Errors ab.

### `tool_result_max_chars` (Commit `6d1ff0e`)

Live-Truncation pro Tool-Result vor Aufnahme in die History. Verhindert
dass ein einzelner riesiger Output (z.B. `gh issue list` mit 50k JSON) den
ganzen Context frisst. Default 12000, per-Agent konfigurierbar.

### Anti-Brute-Force (#113-Fix, Commit `71dc30f`)

Longterm-Memory-Prompt enthält explizite "Empty-Search-Budget"-Regel:
nach 2× `count: 0` aufhören mit Query-Variationen. Brute-Force durch Synonyme
verbrennt sonst Tokens (verifiziert: −49% Token-Verbrauch).

## Wichtige Dateien

| Datei | Verantwortung |
|---|---|
| `runner/runner.py` | Top-Level-Orchestrierung, Event-Stream |
| `runner/_runner_iter.py` | `prepare_history`, `build_system_prompts`, `stream_llm_call` |
| `runner/_runner_tools.py` | `process_tool_uses`, Result-Truncation |
| `runner/_runner_setup.py` | Longterm-Memory-Tool-Injection |
| `runner/_call.py` | Stream-or-Fallback-Wrapper, `CallResult`-Dataclass |
| `runner/llm_bridge.py` | Provider-Switch (claude/minimax/codex/litellm) |
| `runner/_llm_bridge_backends.py` | Non-streaming Backend-Calls (anthropic_call etc.) |
| `runner/llm_bridge_stream.py` | Streaming-Wrapper, Provider-Switch |
| `runner/_stream_providers.py` | Stream-Implementierungen pro Provider |
| `runner/_codex_provider.py` | ChatGPT Plus/Pro über Codex-Backend |
| `runner/context.py` | History-Konvertierung, Orphan-Healing |
| `runner/_token_usage.py` | `usage_dict`, `usage_from_litellm` |
| `runner/dispatcher.py` | Tool-Dispatch + Live-Truncation |
| `runner/tool_confirmation.py` | Pending Tool-Confirmation-Futures |
| `runner/events.py` | Event-Dataclasses (Done, Error, ToolCall…) |

## Tests

- `test_runner_context.py` (24) — pure Functions: extract_tool_uses, heal_orphans, dispatcher
- `test_runner_cache.py` (12) — Anthropic Prompt-Cache (Stable/Volatile/1h-TTL)
- `test_token_usage.py` (8) — Token-Extraction-Helper
- `test_reasoning_effort.py` (13) — Thinking-Block-Generierung
