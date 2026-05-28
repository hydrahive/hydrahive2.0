CREATE TABLE IF NOT EXISTS ega_records (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    dto_type    TEXT NOT NULL,
    display     TEXT NOT NULL DEFAULT '',
    sort_date   TEXT,
    record_json TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ega_user_type ON ega_records(user_id, dto_type);
CREATE INDEX IF NOT EXISTS idx_ega_user_date ON ega_records(user_id, sort_date);
