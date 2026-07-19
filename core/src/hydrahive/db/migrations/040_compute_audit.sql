-- 040: Append-only security audit for compute-cluster administration.
CREATE TABLE IF NOT EXISTS compute_audit_log (
    audit_id       TEXT PRIMARY KEY,
    actor          TEXT NOT NULL,
    action         TEXT NOT NULL,
    node_id        TEXT,
    details_json   TEXT,
    created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_compute_audit_created ON compute_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_compute_audit_node ON compute_audit_log(node_id, created_at DESC);

CREATE TRIGGER IF NOT EXISTS compute_audit_no_update
BEFORE UPDATE ON compute_audit_log
BEGIN
    SELECT RAISE(ABORT, 'compute_audit_is_append_only');
END;

CREATE TRIGGER IF NOT EXISTS compute_audit_no_delete
BEFORE DELETE ON compute_audit_log
BEGIN
    SELECT RAISE(ABORT, 'compute_audit_is_append_only');
END;
