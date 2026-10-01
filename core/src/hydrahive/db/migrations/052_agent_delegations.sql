-- Hintergrund-Aufträge an Spezialisten (docs/specs/agent-background-delegation.md).
-- ask_agent kehrt im Chat sofort zurück; das Ergebnis wird später als eigene
-- Nachricht in die Session des Auftraggebers zugestellt.
CREATE TABLE IF NOT EXISTS agent_delegations (
    id                TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id          TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    target_agent_id   TEXT NOT NULL,
    target_name       TEXT NOT NULL,
    task              TEXT NOT NULL,
    state_id          TEXT NOT NULL UNIQUE,
    depth             INTEGER NOT NULL DEFAULT 1,
    status            TEXT NOT NULL DEFAULT 'running',
    result            TEXT,
    created_at        TEXT NOT NULL,
    deadline_at       TEXT NOT NULL,
    finished_at       TEXT,
    delivered_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_delegations_session
    ON agent_delegations(session_id, status);
