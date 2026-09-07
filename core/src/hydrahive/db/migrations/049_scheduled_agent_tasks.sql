-- Persistent direct agent/buddy schedules.
CREATE TABLE scheduled_agent_tasks (
    task_id          TEXT PRIMARY KEY,
    owner            TEXT NOT NULL,
    scope            TEXT NOT NULL DEFAULT 'user' CHECK (scope IN ('user', 'project')),
    project_id       TEXT,
    target_type      TEXT NOT NULL CHECK (target_type IN ('agent', 'buddy')),
    target_id        TEXT NOT NULL,
    title            TEXT NOT NULL,
    prompt           TEXT NOT NULL,
    execution_mode   TEXT NOT NULL DEFAULT 'direct' CHECK (execution_mode IN ('direct', 'butler_event')),
    interval_seconds INTEGER NOT NULL CHECK (interval_seconds >= 10),
    enabled          INTEGER NOT NULL DEFAULT 1,
    running          INTEGER NOT NULL DEFAULT 0,
    next_run_at      TEXT NOT NULL,
    last_run_at      TEXT,
    last_status      TEXT NOT NULL DEFAULT 'never',
    last_error       TEXT,
    failure_count    INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE INDEX idx_sat_owner ON scheduled_agent_tasks(owner);
CREATE INDEX idx_sat_project ON scheduled_agent_tasks(project_id);
CREATE INDEX idx_sat_due ON scheduled_agent_tasks(enabled, running, next_run_at);

CREATE TABLE scheduled_agent_task_runs (
    run_id      TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL REFERENCES scheduled_agent_tasks(task_id) ON DELETE CASCADE,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,
    session_id  TEXT,
    error       TEXT
);
CREATE INDEX idx_satr_task ON scheduled_agent_task_runs(task_id, started_at DESC);
