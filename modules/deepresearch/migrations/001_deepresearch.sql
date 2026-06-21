CREATE TABLE IF NOT EXISTS module_research_runs (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    question TEXT NOT NULL,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'running',   -- running | done | error
    category TEXT NOT NULL DEFAULT 'general',
    progress_json TEXT NOT NULL DEFAULT '{}',  -- live: round, queries, urls
    result_json TEXT,                          -- {markdown, sources, stats}
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_research_runs_user ON module_research_runs (username, created_at DESC);
