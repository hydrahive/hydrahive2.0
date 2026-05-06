CREATE TABLE IF NOT EXISTS agent_handoffs (
    id                TEXT PRIMARY KEY,
    incoming_state_id TEXT NOT NULL,
    from_agent        TEXT NOT NULL,
    agent_id          TEXT NOT NULL,
    session_id        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'running',
    started_at        TEXT NOT NULL,
    completed_at      TEXT
);
