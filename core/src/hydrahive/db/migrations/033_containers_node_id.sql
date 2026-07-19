-- 033: Bind every container to a compute node; existing rows remain local.
ALTER TABLE containers ADD COLUMN node_id TEXT NOT NULL DEFAULT 'local';
