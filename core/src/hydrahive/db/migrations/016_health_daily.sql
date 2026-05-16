CREATE TABLE IF NOT EXISTS health_daily (
    date        TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    unit        TEXT NOT NULL DEFAULT '',
    value       REAL NOT NULL,
    PRIMARY KEY (date, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_health_daily_date ON health_daily (date);
