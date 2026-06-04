-- FHIR/eGA-Import-Stores (read-only Blob-Stores, getrennt von der relationalen Akte).
-- Additive IF-NOT-EXISTS-Kopie der Core-Migrationen 021+022; Core legt die Tabellen
-- weiterhin an, diese Migration ist No-op auf bestehenden DBs (Selbst-Absicherung
-- für frische Installationen). Daten bleiben.

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

CREATE TABLE IF NOT EXISTS ega_records (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    dto_type    TEXT NOT NULL,
    display     TEXT NOT NULL DEFAULT '',
    sort_date   TEXT,
    record_json TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ega_user_type ON ega_records(user_id, dto_type);
CREATE INDEX IF NOT EXISTS idx_ega_user_date ON ega_records(user_id, sort_date);
