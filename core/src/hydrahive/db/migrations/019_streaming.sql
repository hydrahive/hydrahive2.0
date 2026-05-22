CREATE TABLE IF NOT EXISTS streaming_credentials (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    user_id     TEXT NOT NULL,
    provider    TEXT NOT NULL DEFAULT 'ghostflix',
    username    TEXT NOT NULL,
    password_enc TEXT NOT NULL,
    plex_path   TEXT NOT NULL DEFAULT '/media/plex',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, provider)
);

CREATE TABLE IF NOT EXISTS streaming_jobs (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    user_id         TEXT NOT NULL,
    provider        TEXT NOT NULL DEFAULT 'ghostflix',
    series_title    TEXT NOT NULL,
    series_url      TEXT NOT NULL,
    season          INTEGER NOT NULL DEFAULT 1,
    episode         INTEGER NOT NULL,
    episode_key     TEXT NOT NULL,
    bunny_video_id  TEXT NOT NULL,
    bunny_library_id TEXT NOT NULL,
    output_path     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    progress        INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
