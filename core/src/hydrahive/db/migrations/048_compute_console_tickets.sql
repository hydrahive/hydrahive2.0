-- 048: Short-lived, one-time, resource-bound console tickets.
-- Tickets authorize a single console session to exactly one remote resource on
-- one node. Only the HMAC of the ticket secret is stored, never the secret.
CREATE TABLE IF NOT EXISTS compute_console_tickets (
    ticket_id      TEXT PRIMARY KEY,
    ticket_hmac    TEXT NOT NULL UNIQUE,
    node_id        TEXT NOT NULL,
    resource_kind  TEXT NOT NULL,              -- 'container' | 'vm'
    resource_id    TEXT NOT NULL,
    created_by     TEXT NOT NULL,
    expires_at     TEXT NOT NULL,
    consumed_at    TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_console_tickets_expiry ON compute_console_tickets(expires_at);
CREATE INDEX IF NOT EXISTS idx_console_tickets_resource ON compute_console_tickets(resource_kind, resource_id);
