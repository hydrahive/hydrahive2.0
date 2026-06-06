CREATE TABLE IF NOT EXISTS module_tasks (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    project_id TEXT,
    session_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_tasks_username ON module_tasks (username);
CREATE INDEX IF NOT EXISTS idx_module_tasks_status ON module_tasks (username, status);
