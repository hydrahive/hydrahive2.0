# Plan: Codex Context und Cache

## Ziel

HydraHive verwendet für Codex-OAuth die offiziellen nutzbaren Kontextfenster, berechnet Compaction und Tokenmeter anhand des effektiven Session-Modells, übergibt das Output-Limit und bewahrt verschlüsselte Reasoning-Items für zustandslose Folgeaufrufe. OpenAIs automatischer Prompt-Cache wird korrekt gemessen.

## Dateien

- `core/src/hydrahive/llm/_catalog_data.py` — offizielle Codex-OAuth-Fenster.
- `core/src/hydrahive/runner/runner.py` — effektives Modell vor Compaction bestimmen.
- `core/src/hydrahive/api/routes/sessions_messages.py` — Tokenmeter nutzt Session-Override.
- `core/src/hydrahive/runner/_codex_provider.py` — max_output_tokens, Reasoning-Items, cached_tokens.
- `core/src/hydrahive/runner/_codex_convert.py` — verschlüsselten Reasoning-State modellgebunden replayen.
- `core/src/hydrahive/runner/_call.py` — internen Codex-State sicher persistieren.
- `frontend/src/features/agents/CompactionSection.tsx` — UI-Fallbacks an Backend-Defaults angleichen.
- `core/tests/test_codex_context.py` — Kontext-, Payload-, Replay- und Override-Tests.

## Reihenfolge

1. Offizielle Context-Windows eintragen und testen.
2. Effektives Session-Modell für Compaction/Tokenmeter verwenden.
3. Codex-Payload um Output-Limit ergänzen.
4. Reasoning-Items aus SSE erfassen, intern speichern und nur beim gleichen Codex-Modell replayen.
5. Cache-Telemetrie über `usage.input_tokens_details.cached_tokens` verifizieren.
6. UI-Fallbacks korrigieren; Tests, Ruff und Build ausführen.

## Akzeptanzkriterien

- GPT-5.6 nutzt 372k, GPT-5.5/5.4/5.4-mini 272k im Codex-OAuth-Pfad.
- Session-Modelloverride bestimmt Tokenmeter und Compaction.
- Codex erhält `max_output_tokens`.
- Verschlüsseltes Reasoning wird gespeichert und beim selben Modell erneut gesendet, bei Modellwechsel nicht.
- Cache-Hits erscheinen weiterhin als `cache_read_tokens`.
- Keine Secrets oder entschlüsseltes internes Reasoning werden gespeichert.
