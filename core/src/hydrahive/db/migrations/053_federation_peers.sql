-- Server-Kopplung HydraHive ↔ HydraHive (docs/specs/server-peering.md).
-- Ein Partner-Server ist erst nach Fingerprint-Bestätigung durch den Admin
-- aktiv. Pro Partner sind nur ausdrücklich freigegebene Agenten erreichbar.
CREATE TABLE IF NOT EXISTS federation_peers (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    url           TEXT NOT NULL,
    public_key    TEXT NOT NULL UNIQUE,
    fingerprint   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL,
    confirmed_at  TEXT,
    last_seen     TEXT
);

CREATE TABLE IF NOT EXISTS federation_peer_agents (
    peer_id   TEXT NOT NULL REFERENCES federation_peers(id) ON DELETE CASCADE,
    agent_id  TEXT NOT NULL,
    PRIMARY KEY (peer_id, agent_id)
);

-- Replay-Schutz und Zuordnung der Antworten (Etappe 2).
CREATE TABLE IF NOT EXISTS federation_peer_tasks (
    task_id         TEXT PRIMARY KEY,
    peer_id         TEXT NOT NULL REFERENCES federation_peers(id) ON DELETE CASCADE,
    direction       TEXT NOT NULL,
    local_state_id  TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_federation_peer_tasks_peer ON federation_peer_tasks (peer_id);
