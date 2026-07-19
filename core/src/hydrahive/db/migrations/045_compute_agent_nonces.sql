-- 045: Bounded replay protection for agent protocol messages.
CREATE TABLE IF NOT EXISTS compute_agent_nonces (
    node_id     TEXT NOT NULL REFERENCES compute_nodes(node_id) ON DELETE CASCADE,
    nonce       TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    PRIMARY KEY (node_id, nonce)
);

CREATE INDEX IF NOT EXISTS idx_compute_agent_nonces_expiry
ON compute_agent_nonces(expires_at);
