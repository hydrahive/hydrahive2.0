-- 021_fhir_resources.sql
CREATE TABLE IF NOT EXISTS fhir_resources (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT NOT NULL,
    resource_json TEXT NOT NULL,
    imported_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fhir_unique
    ON fhir_resources(user_id, resource_type, resource_id);

CREATE INDEX IF NOT EXISTS idx_fhir_user_type
    ON fhir_resources(user_id, resource_type);

CREATE INDEX IF NOT EXISTS idx_fhir_user_id
    ON fhir_resources(user_id);
