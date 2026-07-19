-- 036: Monotonic VM configuration generation.
ALTER TABLE vms ADD COLUMN generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0);
