CREATE TABLE IF NOT EXISTS module_ai_security_scans (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    scan_type TEXT NOT NULL,
    target_url TEXT NOT NULL,
    upstream_session_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    result_json TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_security_scans_owner_created
    ON module_ai_security_scans (username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_security_scans_status_updated
    ON module_ai_security_scans (status, updated_at);
