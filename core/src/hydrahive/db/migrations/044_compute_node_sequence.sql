-- 044: Persist agent protocol sequence across reconnects.
ALTER TABLE compute_nodes
ADD COLUMN last_sequence INTEGER NOT NULL DEFAULT 0 CHECK (last_sequence >= 0);
