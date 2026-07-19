-- 041: Idempotent recovery records for successful agent enrollments.
CREATE TABLE IF NOT EXISTS compute_enrollment_results (
    token_id                TEXT PRIMARY KEY REFERENCES compute_enrollment_tokens(token_id) ON DELETE RESTRICT,
    csr_sha256              TEXT NOT NULL,
    node_id                 TEXT NOT NULL UNIQUE REFERENCES compute_nodes(node_id) ON DELETE RESTRICT,
    certificate_pem         TEXT NOT NULL,
    certificate_expires_at  TEXT NOT NULL,
    created_at              TEXT NOT NULL
);
