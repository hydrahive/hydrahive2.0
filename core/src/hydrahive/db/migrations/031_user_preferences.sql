-- 031: Per-user UI/cockpit preferences.

CREATE TABLE user_preferences (
    user_id     TEXT PRIMARY KEY,
    preferences TEXT NOT NULL DEFAULT '{}',
    updated_at  TEXT NOT NULL
);
