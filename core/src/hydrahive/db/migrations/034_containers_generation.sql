-- 034: Monotonic container configuration generation.
ALTER TABLE containers ADD COLUMN generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0);
