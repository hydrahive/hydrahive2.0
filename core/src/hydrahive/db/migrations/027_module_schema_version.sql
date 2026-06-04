-- core/src/hydrahive/db/migrations/027_module_schema_version.sql
CREATE TABLE IF NOT EXISTS module_schema_version (
    module_id   TEXT NOT NULL,
    version     INTEGER NOT NULL,
    applied_at  TEXT NOT NULL,
    PRIMARY KEY (module_id, version)
);
