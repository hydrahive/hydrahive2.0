CREATE TABLE IF NOT EXISTS teamchat_identities (
    user_id       TEXT PRIMARY KEY,
    mxid          TEXT NOT NULL,
    access_token  TEXT NOT NULL,
    device_id     TEXT,
    next_batch    TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS teamchat_rooms (
    room_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS teamchat_room_agents (
    room_id      TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    attached_by  TEXT NOT NULL,
    attached_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (room_id, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_teamchat_room_agents_room ON teamchat_room_agents (room_id);
