-- Apple-Health-Ingest-Store (Endschema nach Core-Migrationen 015+016+020, mit user_id).
-- Additive IF-NOT-EXISTS-Kopie; Core legt die Tabellen via 015/016/020 weiterhin an,
-- diese Migration ist No-op auf bestehenden DBs. Daten bleiben.

CREATE TABLE IF NOT EXISTS health_ingest (
    id              TEXT PRIMARY KEY,
    received_at     TEXT NOT NULL,
    automation_name TEXT,
    automation_id   TEXT,
    session_id      TEXT,
    period          TEXT,
    aggregation     TEXT,
    payload         TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT 'till'
);
CREATE INDEX IF NOT EXISTS idx_health_ingest_received_at ON health_ingest (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_ingest_automation_id ON health_ingest (automation_id);
CREATE INDEX IF NOT EXISTS idx_health_ingest_user_id ON health_ingest (user_id);

CREATE TABLE IF NOT EXISTS health_daily (
    date        TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    user_id     TEXT NOT NULL DEFAULT 'till',
    unit        TEXT NOT NULL DEFAULT '',
    value       REAL NOT NULL,
    PRIMARY KEY (date, metric_name, user_id)
);
CREATE INDEX IF NOT EXISTS idx_health_daily_date ON health_daily (date);
CREATE INDEX IF NOT EXISTS idx_health_daily_user_id ON health_daily (user_id);
