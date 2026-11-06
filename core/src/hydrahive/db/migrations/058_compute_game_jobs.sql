-- 058: Add project-bound, immutable-source Game Studio jobs without changing legacy job semantics.

DROP TRIGGER IF EXISTS compute_nodes_restrict_delete;

CREATE TEMP TABLE compute_job_events_058 AS SELECT * FROM compute_job_events;
DROP TABLE compute_job_events;
ALTER TABLE compute_jobs RENAME TO compute_jobs_legacy_058;

CREATE TABLE compute_jobs (
    job_id                  TEXT PRIMARY KEY,
    node_id                 TEXT NOT NULL REFERENCES compute_nodes(node_id),
    resource_kind           TEXT NOT NULL CHECK (resource_kind IN ('container', 'vm', 'node', 'game_workspace')),
    resource_id             TEXT,
    operation               TEXT NOT NULL,
    generation              INTEGER NOT NULL CHECK (generation >= 0),
    payload_json            TEXT NOT NULL,
    idempotency_key         TEXT NOT NULL UNIQUE,
    status                  TEXT NOT NULL CHECK (
        status IN ('queued', 'leased', 'running', 'succeeded', 'failed', 'cancelled', 'expired')
    ),
    lease_id                TEXT,
    lease_until             TEXT,
    attempts                INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    progress                INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    error_code              TEXT,
    error_params_json       TEXT,
    created_by              TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    started_at              TEXT,
    finished_at             TEXT,
    project_id              TEXT,
    provider                TEXT,
    game_resource_id        TEXT REFERENCES compute_game_workspaces(resource_id),
    workspace_generation    INTEGER CHECK (workspace_generation >= 1),
    source_commit_sha       TEXT,
    source_snapshot_digest  TEXT,
    cancel_requested_by     TEXT,
    cancel_requested_at     TEXT,
    CHECK (
        (resource_kind = 'game_workspace'
         AND project_id IS NOT NULL
         AND provider = 'game-runtime/v1'
         AND game_resource_id IS NOT NULL
         AND resource_id = game_resource_id
         AND workspace_generation IS NOT NULL
         AND generation = workspace_generation
         AND ((source_commit_sha IS NOT NULL AND source_snapshot_digest IS NULL)
              OR (source_commit_sha IS NULL AND source_snapshot_digest IS NOT NULL)))
        OR
        (resource_kind != 'game_workspace'
         AND project_id IS NULL AND provider IS NULL AND game_resource_id IS NULL
         AND workspace_generation IS NULL AND source_commit_sha IS NULL
         AND source_snapshot_digest IS NULL AND cancel_requested_by IS NULL
         AND cancel_requested_at IS NULL)
    ),
    CHECK (
        source_commit_sha IS NULL
        OR (length(source_commit_sha) IN (40, 64) AND source_commit_sha NOT GLOB '*[^0-9a-f]*')
    ),
    CHECK (
        source_snapshot_digest IS NULL
        OR (length(source_snapshot_digest) = 71
            AND substr(source_snapshot_digest, 1, 7) = 'sha256:'
            AND substr(source_snapshot_digest, 8) NOT GLOB '*[^0-9a-f]*')
    ),
    CHECK (
        (cancel_requested_by IS NULL AND cancel_requested_at IS NULL)
        OR (resource_kind = 'game_workspace' AND cancel_requested_by IS NOT NULL AND cancel_requested_at IS NOT NULL)
    )
);

INSERT INTO compute_jobs (
    job_id, node_id, resource_kind, resource_id, operation, generation, payload_json,
    idempotency_key, status, lease_id, lease_until, attempts, progress, error_code,
    error_params_json, created_by, created_at, started_at, finished_at
)
SELECT job_id, node_id, resource_kind, resource_id, operation, generation, payload_json,
       idempotency_key, status, lease_id, lease_until, attempts, progress, error_code,
       error_params_json, created_by, created_at, started_at, finished_at
FROM compute_jobs_legacy_058;
DROP TABLE compute_jobs_legacy_058;

CREATE TABLE compute_job_events (
    event_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id         TEXT NOT NULL REFERENCES compute_jobs(job_id) ON DELETE CASCADE,
    sequence       INTEGER NOT NULL CHECK (sequence >= 0),
    event_type     TEXT NOT NULL,
    data_json      TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    UNIQUE(job_id, sequence)
);
INSERT INTO compute_job_events SELECT * FROM compute_job_events_058;
DROP TABLE compute_job_events_058;

CREATE INDEX idx_compute_jobs_node_status ON compute_jobs(node_id, status);
CREATE INDEX idx_compute_jobs_project_status ON compute_jobs(project_id, status, created_at DESC);
CREATE INDEX idx_compute_job_events_job ON compute_job_events(job_id, sequence);

CREATE TRIGGER compute_game_job_binding_matches_insert
BEFORE INSERT ON compute_jobs
WHEN NEW.resource_kind = 'game_workspace' AND NOT EXISTS (
    SELECT 1 FROM compute_game_workspaces AS workspace
    WHERE workspace.resource_id = NEW.game_resource_id
      AND workspace.project_id = NEW.project_id
      AND workspace.node_id = NEW.node_id
      AND workspace.provider = NEW.provider
      AND workspace.generation = NEW.workspace_generation
)
BEGIN
    SELECT RAISE(ABORT, 'game_execution_binding_mismatch');
END;

CREATE TRIGGER compute_nodes_restrict_delete
BEFORE DELETE ON compute_nodes
WHEN OLD.node_id = 'local'
  OR EXISTS (SELECT 1 FROM containers WHERE node_id = OLD.node_id)
  OR EXISTS (SELECT 1 FROM vms WHERE node_id = OLD.node_id)
  OR EXISTS (SELECT 1 FROM compute_jobs WHERE node_id = OLD.node_id)
  OR EXISTS (SELECT 1 FROM compute_game_workspaces WHERE node_id = OLD.node_id)
  OR EXISTS (SELECT 1 FROM compute_game_isolation_approvals WHERE node_id = OLD.node_id)
BEGIN
    SELECT RAISE(ABORT, 'compute_node_in_use');
END;
