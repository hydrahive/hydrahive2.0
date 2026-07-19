-- 042: Bound retry-safe certificate recovery for completed enrollments.
ALTER TABLE compute_enrollment_results
ADD COLUMN recovery_until TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z';
