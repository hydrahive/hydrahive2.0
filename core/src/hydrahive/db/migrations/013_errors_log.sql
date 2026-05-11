-- errors_log: zentrale Fehler-Tabelle (Token-Audit #129)
-- Erfasst Fehler die heute nur in Logs landen (logger.exception) und damit
-- nach Logrotate verloren sind. Insbesondere:
--  - LLM-Call-Crashes (Runner)
--  - Background-Tasks (compress_session, crystallize_session)
--  - Mirror-Sync-Errors
--  - MCP/Plugin-Crashes mit Detail
-- Tool-Crashes haben bereits eigene Spalten in tool_calls (PR 3).

CREATE TABLE errors_log (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    -- Identity (alle nullable — manche Fehler haben keinen Session-Kontext)
    session_id      TEXT,
    agent_id        TEXT,
    user_id         TEXT,
    -- Klassifikation
    source          TEXT NOT NULL,                -- 'runner.llm_call', 'compress_bg', 'mirror.write_event', ...
    severity        TEXT NOT NULL DEFAULT 'error', -- 'error' | 'warning' | 'critical'
    -- Details
    error_type      TEXT,                         -- Exception-Klasse
    error_message   TEXT,                         -- str(exc)
    traceback       TEXT,                         -- traceback.format_exc()
    context         TEXT                          -- JSON: tool_name, message_id, model, iteration, ...
);

CREATE INDEX idx_errors_log_session  ON errors_log(session_id);
CREATE INDEX idx_errors_log_source   ON errors_log(source);
CREATE INDEX idx_errors_log_severity ON errors_log(severity);
CREATE INDEX idx_errors_log_created  ON errors_log(created_at);
CREATE INDEX idx_errors_log_type     ON errors_log(error_type);
