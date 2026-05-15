---
name: performance-profile
description: Token-Verbrauch und Cache-Hit-Rate analysieren, Optimierungsempfehlungen ableiten
when_to_use: Wenn Sessions ungewöhnlich teuer sind, Cache-Misses auftreten oder Token-Verbrauch optimiert werden soll
tools_required: [shell_exec, file_read]
---

# Performance-Analyse

## Token-Verbrauch einer Session

```bash
# LLM-Calls für eine Session
sqlite3 /var/lib/hydrahive2/sessions.db "
SELECT
  model,
  SUM(input_tokens) as input,
  SUM(output_tokens) as output,
  SUM(cache_creation_tokens) as cache_write,
  SUM(cache_read_tokens) as cache_read,
  COUNT(*) as calls
FROM llm_calls
WHERE session_id = '<session_id>'
GROUP BY model;"
```

## Cache-Hit-Rate berechnen

```bash
sqlite3 /var/lib/hydrahive2/sessions.db "
SELECT
  ROUND(100.0 * SUM(cache_read_tokens) /
    NULLIF(SUM(input_tokens + cache_read_tokens), 0), 1) || '%' as cache_hit_rate,
  SUM(cache_creation_tokens) as cache_written,
  SUM(cache_read_tokens) as cache_read
FROM llm_calls
WHERE created_at > datetime('now', '-1 day');"
```

Zielwert: **>60% Cache-Hit-Rate** für Sessions mit ähnlichem System-Prompt.

## Typische Probleme

| Symptom | Ursache | Fix |
|---------|---------|-----|
| Cache-Hit-Rate 0% | Datum/Uhrzeit im stable_system | Datum in volatile_system verschieben |
| Input-Tokens > 50k | Keine Kompaktierung | compact_threshold_pct senken |
| Viele kleine Calls | max_iterations zu niedrig | max_iterations erhöhen |
| stop_reason=max_tokens | max_tokens zu niedrig | Auf ≥16384 setzen |
| Hohe Cache-Writes | System-Prompt zu groß | Prompt-Diet (#133) |

## Kosten-Schätzung

```bash
sqlite3 /var/lib/hydrahive2/sessions.db "
SELECT
  ROUND(SUM(cost_micros) / 1000000.0, 4) || ' EUR' as total_cost,
  COUNT(DISTINCT session_id) as sessions
FROM llm_calls
WHERE created_at > datetime('now', '-7 days');"
```

## Agent-Config optimieren

- `compact_threshold_pct`: 75 (Standard) — bei Bedarf auf 60 senken
- `max_tokens`: ≥ 16384 für Opus + Thinking
- `cache_ttl`: "1h" für Extended Cache, "5m" sonst
- `tool_result_max_chars`: 12000 (Standard) — bei vielen Tool-Calls reduzieren
