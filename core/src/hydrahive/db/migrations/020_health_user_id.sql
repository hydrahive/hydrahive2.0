-- Health-Daten werden per User isoliert.
-- health_ingest: user_id Spalte hinzufügen (bestehende Daten → 'till')
ALTER TABLE health_ingest ADD COLUMN user_id TEXT NOT NULL DEFAULT 'till';
CREATE INDEX IF NOT EXISTS idx_health_ingest_user_id ON health_ingest (user_id);

-- health_daily: PK muss (date, metric_name, user_id) werden.
-- SQLite erlaubt keinen PK-Alter, daher Tabelle neu aufbauen.
ALTER TABLE health_daily RENAME TO health_daily_old;

CREATE TABLE health_daily (
    date        TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    user_id     TEXT NOT NULL DEFAULT 'till',
    unit        TEXT NOT NULL DEFAULT '',
    value       REAL NOT NULL,
    PRIMARY KEY (date, metric_name, user_id)
);

INSERT INTO health_daily (date, metric_name, user_id, unit, value)
SELECT date, metric_name, 'till', unit, value FROM health_daily_old;

DROP TABLE health_daily_old;

CREATE INDEX IF NOT EXISTS idx_health_daily_date ON health_daily (date);
CREATE INDEX IF NOT EXISTS idx_health_daily_user_id ON health_daily (user_id);
