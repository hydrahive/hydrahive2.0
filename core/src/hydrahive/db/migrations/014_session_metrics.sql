-- session_metrics: Aggregierter Read-View über die Telemetrie-Tabellen
-- Aus Token-Audit #129 (PR 5/5). Drift-frei: always-recompute beim SELECT.
-- Wenn das später zu langsam wird können wir auf inkrementelle Aggregate
-- in sessions umstellen — aber jetzt erst messen, nicht optimieren.

CREATE VIEW session_metrics AS
SELECT
    s.id                                       AS session_id,
    s.agent_id, s.user_id, s.project_id,
    s.created_at, s.updated_at, s.status,
    -- LLM-Aggregate
    COALESCE(llm.calls, 0)                     AS llm_calls,
    COALESCE(llm.input_tokens, 0)              AS input_tokens,
    COALESCE(llm.output_tokens, 0)             AS output_tokens,
    COALESCE(llm.cache_read_tokens, 0)         AS cache_read_tokens,
    COALESCE(llm.cache_creation_tokens, 0)     AS cache_creation_tokens,
    COALESCE(llm.cost_micros, 0)               AS cost_micros,
    COALESCE(llm.total_llm_ms, 0)              AS total_llm_ms,
    -- Tool-Aggregate (nur Calls mit session_id — alte PR2-Zeilen NULL → ignoriert)
    COALESCE(tc.calls, 0)                      AS tool_calls,
    COALESCE(tc.successes, 0)                  AS tool_successes,
    COALESCE(tc.errors, 0)                     AS tool_errors,
    COALESCE(tc.truncates, 0)                  AS tool_truncates,
    COALESCE(tc.total_duration_ms, 0)          AS tool_total_ms,
    -- Compaction-Aggregate
    COALESCE(cmp.events, 0)                    AS compactions,
    COALESCE(cmp.skipped, 0)                   AS compactions_skipped,
    -- Error-Aggregate
    COALESCE(err.events, 0)                    AS errors
FROM sessions s
LEFT JOIN (
    SELECT session_id,
           COUNT(*)                            AS calls,
           SUM(prompt_tokens)                  AS input_tokens,
           SUM(completion_tokens)              AS output_tokens,
           SUM(cache_read_tokens)              AS cache_read_tokens,
           SUM(cache_creation_tokens)          AS cache_creation_tokens,
           SUM(cost_micros)                    AS cost_micros,
           SUM(total_ms)                       AS total_llm_ms
    FROM llm_calls GROUP BY session_id
) llm ON llm.session_id = s.id
LEFT JOIN (
    SELECT session_id,
           COUNT(*)                                              AS calls,
           SUM(CASE WHEN status='success' THEN 1 ELSE 0 END)     AS successes,
           SUM(CASE WHEN status='error' THEN 1 ELSE 0 END)       AS errors,
           SUM(CASE WHEN result_truncated=1 THEN 1 ELSE 0 END)   AS truncates,
           SUM(duration_ms)                                      AS total_duration_ms
    FROM tool_calls WHERE session_id IS NOT NULL GROUP BY session_id
) tc ON tc.session_id = s.id
LEFT JOIN (
    SELECT session_id,
           COUNT(*)                                              AS events,
           SUM(CASE WHEN skipped=1 THEN 1 ELSE 0 END)            AS skipped
    FROM compaction_events GROUP BY session_id
) cmp ON cmp.session_id = s.id
LEFT JOIN (
    SELECT session_id, COUNT(*) AS events
    FROM errors_log WHERE session_id IS NOT NULL GROUP BY session_id
) err ON err.session_id = s.id;
