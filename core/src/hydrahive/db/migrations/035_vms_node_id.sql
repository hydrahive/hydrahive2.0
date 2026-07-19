-- 035: Bind every VM to a compute node; existing rows remain local.
ALTER TABLE vms ADD COLUMN node_id TEXT NOT NULL DEFAULT 'local';
