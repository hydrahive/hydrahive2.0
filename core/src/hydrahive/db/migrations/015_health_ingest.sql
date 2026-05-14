CREATE TABLE IF NOT EXISTS health_ingest (
    id              TEXT PRIMARY KEY,
    received_at     TEXT NOT NULL,
    automation_name TEXT,
    automation_id   TEXT,
    session_id      TEXT,
    period          TEXT,
    aggregation     TEXT,
    payload         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_health_ingest_received_at ON health_ingest (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_ingest_automation_id ON health_ingest (automation_id);
