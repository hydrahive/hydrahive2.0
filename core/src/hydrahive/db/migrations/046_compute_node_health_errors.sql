-- 046: Persist bounded structured health errors reported by agents.
ALTER TABLE compute_nodes
ADD COLUMN health_errors_json TEXT NOT NULL DEFAULT '[]';
