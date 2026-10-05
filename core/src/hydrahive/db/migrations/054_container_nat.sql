-- Container im NAT-Netz und Portfreigaben (docs/specs/container-nat-ports.md).
-- network_mode erlaubt jetzt zusätzlich 'nat'. Die feste interne IP steht in ipv4.
ALTER TABLE containers ADD COLUMN ipv4 TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_containers_ipv4 ON containers(ipv4) WHERE ipv4 IS NOT NULL;

CREATE TABLE IF NOT EXISTS container_ports (
    id                    TEXT PRIMARY KEY,
    container_id          TEXT NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    protocol              TEXT NOT NULL,              -- tcp|udp
    host_port_start       INTEGER NOT NULL,
    host_port_end         INTEGER NOT NULL,
    container_port_start  INTEGER NOT NULL,
    scope                 TEXT NOT NULL DEFAULT 'off', -- public|tailnet|off
    label                 TEXT NOT NULL DEFAULT '',
    created_at            TEXT NOT NULL,
    applied_at            TEXT,
    last_error            TEXT
);

CREATE INDEX IF NOT EXISTS idx_container_ports_container ON container_ports(container_id);
