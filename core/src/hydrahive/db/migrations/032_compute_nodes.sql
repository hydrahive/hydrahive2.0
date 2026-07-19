-- 032: Compute-cluster foundation: node registry, enrollment/job persistence,
-- and additive placement metadata for existing local resources.

CREATE TABLE compute_nodes (
    node_id                  TEXT PRIMARY KEY,
    name                     TEXT NOT NULL UNIQUE,
    kind                     TEXT NOT NULL CHECK (kind IN ('local', 'agent')),
    status                   TEXT NOT NULL CHECK (
        status IN ('pending', 'online', 'degraded', 'offline', 'draining', 'disabled', 'revoked')
    ),
    certificate_fingerprint  TEXT UNIQUE,
    protocol_version         INTEGER NOT NULL CHECK (protocol_version >= 1),
    agent_version            TEXT,
    capabilities_json        TEXT NOT NULL,
    resources_json           TEXT NOT NULL,
    labels_json              TEXT NOT NULL,
    last_seen_at             TEXT,
    approved_at              TEXT,
    approved_by              TEXT,
    revoked_at               TEXT,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL
);

INSERT INTO compute_nodes (
    node_id, name, kind, status, protocol_version,
    capabilities_json, resources_json, labels_json, created_at, updated_at
) VALUES (
    'local', 'Local Host', 'local', 'online', 1,
    '{}', '{}', '{}', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
) ON CONFLICT(node_id) DO NOTHING;

CREATE TABLE compute_enrollment_tokens (
    token_id         TEXT PRIMARY KEY,
    token_hmac       TEXT NOT NULL UNIQUE,
    requested_name   TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    consumed_at      TEXT,
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE compute_jobs (
    job_id               TEXT PRIMARY KEY,
    node_id               TEXT NOT NULL REFERENCES compute_nodes(node_id),
    resource_kind         TEXT NOT NULL CHECK (resource_kind IN ('container', 'vm', 'node')),
    resource_id           TEXT,
    operation             TEXT NOT NULL,
    generation            INTEGER NOT NULL CHECK (generation >= 0),
    payload_json          TEXT NOT NULL,
    idempotency_key       TEXT NOT NULL UNIQUE,
    status                TEXT NOT NULL CHECK (
        status IN ('queued', 'leased', 'running', 'succeeded', 'failed', 'cancelled', 'expired')
    ),
    lease_id              TEXT,
    lease_until           TEXT,
    attempts              INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    progress              INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    error_code            TEXT,
    error_params_json     TEXT,
    created_by            TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    started_at            TEXT,
    finished_at           TEXT
);

CREATE TABLE compute_job_events (
    event_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id         TEXT NOT NULL REFERENCES compute_jobs(job_id) ON DELETE CASCADE,
    sequence       INTEGER NOT NULL CHECK (sequence >= 0),
    event_type     TEXT NOT NULL,
    data_json      TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    UNIQUE(job_id, sequence)
);

CREATE INDEX idx_compute_nodes_status ON compute_nodes(status);
CREATE INDEX idx_compute_jobs_node_status ON compute_jobs(node_id, status);
CREATE INDEX idx_compute_job_events_job ON compute_job_events(job_id, sequence);

ALTER TABLE containers ADD COLUMN node_id TEXT NOT NULL DEFAULT 'local';
ALTER TABLE containers ADD COLUMN generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0);
CREATE INDEX idx_containers_node_id ON containers(node_id);

ALTER TABLE vms ADD COLUMN node_id TEXT NOT NULL DEFAULT 'local';
ALTER TABLE vms ADD COLUMN generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0);
CREATE INDEX idx_vms_node_id ON vms(node_id);
