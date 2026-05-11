-- tool_calls: Telemetrie-Spalten für Token-Audit #129
-- ALTER TABLE ADD COLUMN — alle nullable damit historische Zeilen NULL
-- bleiben (NULL ≠ 0 — "wussten wir damals nicht" vs "war 0").
-- SQLite-Limit: keine FK in ALTER, alle Spalten ohne DEFAULT (außer NULL).

ALTER TABLE tool_calls ADD COLUMN session_id TEXT;
ALTER TABLE tool_calls ADD COLUMN agent_id TEXT;
ALTER TABLE tool_calls ADD COLUMN user_id TEXT;
ALTER TABLE tool_calls ADD COLUMN tool_use_id TEXT;
ALTER TABLE tool_calls ADD COLUMN iteration INTEGER;
ALTER TABLE tool_calls ADD COLUMN arguments_size_bytes INTEGER;
ALTER TABLE tool_calls ADD COLUMN result_size_bytes INTEGER;
ALTER TABLE tool_calls ADD COLUMN result_truncated INTEGER;
ALTER TABLE tool_calls ADD COLUMN truncate_limit_chars INTEGER;
ALTER TABLE tool_calls ADD COLUMN error_type TEXT;
ALTER TABLE tool_calls ADD COLUMN error_message TEXT;

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_agent ON tool_calls(agent_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_calls_created ON tool_calls(created_at);
CREATE INDEX IF NOT EXISTS idx_tool_calls_status ON tool_calls(status);
