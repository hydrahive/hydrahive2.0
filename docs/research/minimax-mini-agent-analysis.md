# Mini-Agent Analyse — MiniMax-AI/Mini-Agent

**Quelle:** https://github.com/MiniMax-AI/Mini-Agent

## Session Note Tool

Mini-Agent persistiert ein Agenten-Scratchpad über Session-Grenzen hinweg.
Das Tool hat zwei Operationen:
- `read_session_note()` — liest den aktuellen Scratchpad-Inhalt
- `write_session_note(content)` — überschreibt den Scratchpad vollständig

**Ablauf:** Agent ruft `read_session_note` am Anfang jeder Session auf,
notiert wichtige Erkenntnisse während der Session mit `write_session_note`.

**Dateiformat:** Plaintext, kein strukturiertes Schema. Der Agent entscheidet
selbst was er aufschreibt.

**Empfehlung für HydraHive:** Session Note Tool als Standard-Tool für
langlebige Agenten einbauen. Einfaches Key-Value-Store in der SQLite-DB,
getaggt per `agent_id`.

## Context Compaction

Mini-Agent triggert automatische Zusammenfassung wenn die Message-History
einen konfigurierbaren Token-Threshold überschreitet (Standard: 80% des
Modell-Kontextfensters).

**Kompaktierungs-Prompt (sinngemäß aus Mini-Agent Source):**
```
Fasse die bisherige Konversation präzise zusammen. Behalte:
- Den ursprünglichen Auftrag
- Alle erledigten Schritte und ihre Ergebnisse
- Den aktuellen Stand und nächste geplante Schritte
- Alle wichtigen Fakten, Dateipfade, Variablen
```

**Empfehlung für HydraHive:** HydraHive hat bereits Compaction-Logik.
Der Mini-Agent-Ansatz ist simpler (kein separater Summary-Block) —
bei Bedarf als Alternative evaluieren.

## Agent-Loop

```
1. check_and_compact_history()   — Token-Check, ggf. Zusammenfassung
2. llm_call(messages, tools)     — Thinking + Tool-Planung
3. for each tool_call:
     result = execute_tool(tc)
     messages.append(tool_result)
4. if stop_reason == "end_turn": break
5. goto 1
```

**Besonderheit:** Interleaved Thinking ist im Loop implizit aktiv —
Thinking-Blöcke werden als Teil der assistant-Message erhalten und
beim nächsten Turn mitgegeben.

## System-Prompt Muster für MiniMax-Modelle

Mini-Agent nutzt kurze, direkte System-Prompts ohne Persona-Block:
```
You are a helpful assistant with access to tools.
Think carefully before each tool call about what information you need.
After each tool result, evaluate whether your plan still holds.
```

Kein "You are Claude Code" o.ä. — MiniMax-Modelle reagieren besser
auf direkte Instruktionen als auf Anthropic-spezifische Personas.

## Key Takeaways

1. Session Note Tool = einfaches Agenten-Gedächtnis, lohnt sich als HydraHive-Feature
2. Context Compaction ist ein expliziter Loop-Schritt, kein Hintergrundprozess
3. Kurze System-Prompts funktionieren bei MiniMax besser als lange
4. Interleaved Thinking wird durch den regulären Anthropic-SDK-Pfad aktiviert — kein Sondercode nötig
5. Mini-Agent hat 15 vordefinierte Skills (Docs, Design, Testing, Dev) — Inspiration für HydraHive-Agenten-Profile
