-- 004: Container-Management (LXC via incus).
--
-- Per-User-Owner. desired_state vs actual_state wie bei VMs.
-- incus_name == DB-name (ein Container pro VM-Name pro Owner global eindeutig).

CREATE TABLE containers (
    container_id   TEXT PRIMARY KEY,
    owner          TEXT NOT NULL,
    name           TEXT NOT NULL UNIQUE,         -- = incus instance name
    description    TEXT,
    image          TEXT NOT NULL,                -- z.B. "images:debian/12"
    cpu            INTEGER,                      -- limits.cpu, NULL = unbegrenzt
    ram_mb         INTEGER,                      -- limits.memory, NULL = unbegrenzt
    network_mode   TEXT NOT NULL DEFAULT 'bridged',  -- bridged|isolated
    desired_state  TEXT NOT NULL DEFAULT 'stopped',
    actual_state   TEXT NOT NULL DEFAULT 'created',
    last_error_code  TEXT,
    last_error_params TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE INDEX idx_containers_owner ON containers(owner);
CREATE INDEX idx_containers_actual_state ON containers(actual_state);

CREATE TABLE container_snapshots (
    snapshot_id  TEXT PRIMARY KEY,
    container_id TEXT NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    description  TEXT,
    created_at   TEXT NOT NULL
);

CREATE INDEX idx_csnap_container ON container_snapshots(container_id);
