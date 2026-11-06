-- 057: Project-bound Game Studio workspace resources and audited isolation approvals.

CREATE TABLE IF NOT EXISTS compute_game_isolation_approvals (
    approval_id          TEXT PRIMARY KEY,
    node_id              TEXT NOT NULL REFERENCES compute_nodes(node_id),
    isolation_profile_id TEXT NOT NULL,
    runner_version       TEXT NOT NULL,
    policy_digest        TEXT NOT NULL,
    proof_digest         TEXT NOT NULL,
    status               TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
    approved_by          TEXT NOT NULL,
    approved_at          TEXT NOT NULL,
    revoked_by           TEXT,
    revoked_at           TEXT,
    UNIQUE(node_id, isolation_profile_id, runner_version, policy_digest, proof_digest),
    CHECK (
        (status = 'active' AND revoked_by IS NULL AND revoked_at IS NULL)
        OR (status = 'revoked' AND revoked_by IS NOT NULL AND revoked_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS compute_game_workspaces (
    resource_id             TEXT PRIMARY KEY,
    provider                TEXT NOT NULL DEFAULT 'game-runtime/v1' CHECK (provider = 'game-runtime/v1'),
    project_id              TEXT NOT NULL,
    node_id                 TEXT NOT NULL REFERENCES compute_nodes(node_id),
    workspace_handle        TEXT NOT NULL,
    engine                  TEXT NOT NULL CHECK (engine IN ('unknown', 'godot', 'unreal')),
    engine_version          TEXT,
    engine_project_relpath  TEXT NOT NULL DEFAULT '.',
    trust_mode              TEXT NOT NULL CHECK (trust_mode IN ('inventory_only', 'sandboxed')),
    status                  TEXT NOT NULL CHECK (
        status IN ('pending', 'ready', 'offline', 'incompatible', 'revoked', 'error')
    ),
    isolation_approval_id   TEXT NOT NULL REFERENCES compute_game_isolation_approvals(approval_id),
    isolation_profile_id    TEXT NOT NULL,
    runner_version          TEXT NOT NULL,
    policy_digest           TEXT NOT NULL,
    generation              INTEGER NOT NULL DEFAULT 1 CHECK (generation >= 1),
    created_by              TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL,
    last_seen_at            TEXT,
    revoked_at              TEXT,
    CHECK (
        (status = 'revoked' AND revoked_at IS NOT NULL)
        OR (status != 'revoked' AND revoked_at IS NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_compute_game_workspaces_active_project
    ON compute_game_workspaces(project_id)
    WHERE status != 'revoked' AND revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_compute_game_workspaces_project
    ON compute_game_workspaces(project_id, generation DESC);
CREATE INDEX IF NOT EXISTS idx_compute_game_workspaces_node_status
    ON compute_game_workspaces(node_id, status);
CREATE INDEX IF NOT EXISTS idx_compute_game_approvals_node_status
    ON compute_game_isolation_approvals(node_id, status);

CREATE TRIGGER IF NOT EXISTS compute_game_workspace_approval_matches_insert
BEFORE INSERT ON compute_game_workspaces
WHEN NOT EXISTS (
    SELECT 1 FROM compute_game_isolation_approvals AS approval
    WHERE approval.approval_id = NEW.isolation_approval_id
      AND approval.node_id = NEW.node_id
      AND approval.isolation_profile_id = NEW.isolation_profile_id
      AND approval.runner_version = NEW.runner_version
      AND approval.policy_digest = NEW.policy_digest
      AND approval.status = 'active'
)
BEGIN
    SELECT RAISE(ABORT, 'game_isolation_approval_invalid');
END;

CREATE TRIGGER IF NOT EXISTS compute_game_workspace_approval_matches_update
BEFORE UPDATE OF node_id, isolation_approval_id, isolation_profile_id, runner_version, policy_digest
ON compute_game_workspaces
WHEN NEW.status != 'revoked' AND NOT EXISTS (
    SELECT 1 FROM compute_game_isolation_approvals AS approval
    WHERE approval.approval_id = NEW.isolation_approval_id
      AND approval.node_id = NEW.node_id
      AND approval.isolation_profile_id = NEW.isolation_profile_id
      AND approval.runner_version = NEW.runner_version
      AND approval.policy_digest = NEW.policy_digest
      AND approval.status = 'active'
)
BEGIN
    SELECT RAISE(ABORT, 'game_isolation_approval_invalid');
END;

-- Extend the existing physical-delete guard so callers receive the same stable
-- compute_node_in_use invariant instead of a late foreign-key error.
DROP TRIGGER IF EXISTS compute_nodes_restrict_delete;
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
