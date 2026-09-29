-- Freigaben und Gruppen, Etappe 1 (docs/specs/access-groups.md §6).
-- Teilen einzelner Sachen (access_resource_shares) folgt in Etappe 2.
-- Alle Nutzer-Verweise über die stabile user_id, nie über den Namen.

CREATE TABLE access_groups (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE access_group_members (
    group_id  TEXT NOT NULL REFERENCES access_groups(id) ON DELETE CASCADE,
    user_id   TEXT NOT NULL,
    added_by  TEXT NOT NULL,
    added_at  TEXT NOT NULL,
    PRIMARY KEY (group_id, user_id)
);
CREATE INDEX idx_access_group_members_user ON access_group_members(user_id);

CREATE TABLE access_capability_grants (
    capability   TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('user', 'group', 'everyone')),
    subject_id   TEXT NOT NULL DEFAULT '',
    level        TEXT NOT NULL CHECK (level IN ('use', 'manage')),
    granted_by   TEXT NOT NULL,
    granted_at   TEXT NOT NULL,
    PRIMARY KEY (capability, subject_type, subject_id)
);
CREATE INDEX idx_access_grants_subject ON access_capability_grants(subject_type, subject_id);

CREATE TABLE access_audit (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT NOT NULL,
    actor_id  TEXT NOT NULL,
    action    TEXT NOT NULL,
    target    TEXT NOT NULL,
    detail    TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_access_audit_target ON access_audit(target, at);
