-- 001: Initial schema for sessions, messages, tool_calls, session_state.

CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    project_id  TEXT,
    user_id     TEXT NOT NULL,
    title       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    metadata    TEXT
);

CREATE INDEX idx_sessions_agent ON sessions(agent_id, updated_at DESC);
CREATE INDEX idx_sessions_user  ON sessions(user_id, updated_at DESC);

CREATE TABLE messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    token_count INTEGER,
    metadata    TEXT
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);

CREATE TABLE tool_calls (
    id          TEXT PRIMARY KEY,
    message_id  TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    tool_name   TEXT NOT NULL,
    arguments   TEXT NOT NULL,
    result      TEXT,
    status      TEXT NOT NULL,
    duration_ms INTEGER,
    created_at  TEXT NOT NULL,
    metadata    TEXT
);

CREATE INDEX idx_tool_calls_message ON tool_calls(message_id);

CREATE TABLE session_state (
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    metadata    TEXT,
    PRIMARY KEY (session_id, key)
);
