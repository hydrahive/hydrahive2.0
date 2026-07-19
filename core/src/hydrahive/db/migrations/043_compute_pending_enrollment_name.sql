-- 043: Allow at most one live enrollment token for a requested node name.
CREATE UNIQUE INDEX IF NOT EXISTS idx_compute_enrollment_pending_name
ON compute_enrollment_tokens(requested_name)
WHERE consumed_at IS NULL;
