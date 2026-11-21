-- Föderations-Katalog: Ideen und Tasks über Server hinweg (docs/specs/federation-catalog.md).
-- Etappe 1: nur Datenmodell + Hub-Markierung, noch kein Versand.
--
-- Reihenfolge wichtig (Spec §Datenmodell): erst alle CREATE TABLE/INDEX IF NOT
-- EXISTS, dann ganz am Ende die beiden ALTER TABLE + Teil-Index. Der
-- Migrations-Runner (db/migrations.py) markiert eine Migration bei
-- "duplicate column name"/"already exists" als vollständig angewendet. Ein
-- Abbruch nach dem ersten ALTER würde die übrigen Tabellen sonst für immer
-- verhindern. Zusätzlich die ganze Migration in BEGIN/COMMIT, denn DDL ist in
-- SQLite transaktional: ein Abbruch zwischen den beiden ALTERs hinterlässt
-- dann gar nichts, und der nächste Start wendet die Migration vollständig an.
BEGIN;

-- Client-Seite: Sync-Einstellungen (eine Zeile).
CREATE TABLE IF NOT EXISTS federation_catalog_settings (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    enabled           INTEGER NOT NULL DEFAULT 0,
    interval_seconds  INTEGER NOT NULL DEFAULT 300,
    seq               INTEGER NOT NULL DEFAULT 0,
    last_push_at      TEXT,
    last_ok_at        TEXT,
    last_full_at      TEXT,
    last_error        TEXT
);

-- Nutzer, deren Ideen und Tasks gesynct werden. Standard: leer.
CREATE TABLE IF NOT EXISTS federation_catalog_users (
    username  TEXT PRIMARY KEY
);

-- Projekte, die nie gesendet werden.
CREATE TABLE IF NOT EXISTS federation_catalog_excluded_projects (
    project_id  TEXT PRIMARY KEY
);

-- Cursor je Nutzer und Art (Tasks/Ideen sind nicht vergleichbar sortiert, Spec
-- §Katalog-Quellen: "einen Cursor je kind").
CREATE TABLE IF NOT EXISTS federation_catalog_cursors (
    username            TEXT NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('task', 'idea')),
    cursor_updated_at  TEXT,
    PRIMARY KEY (username, kind)
);

-- Hub-Seite: gesammelte Metadaten der Clients.
CREATE TABLE IF NOT EXISTS federation_catalog_items (
    peer_id        TEXT NOT NULL REFERENCES federation_peers(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL,
    item_id        TEXT NOT NULL,
    owner          TEXT NOT NULL,
    title          TEXT NOT NULL,
    status         TEXT NOT NULL,
    priority       TEXT,
    project_id     TEXT,
    project_name   TEXT,
    created_at     TEXT,
    updated_at     TEXT,
    received_at    TEXT NOT NULL,
    snapshot_body  TEXT,
    snapshot_at    TEXT,
    PRIMARY KEY (peer_id, kind, item_id)
);

CREATE INDEX IF NOT EXISTS idx_federation_catalog_items_owner_status
    ON federation_catalog_items (owner, status);
CREATE INDEX IF NOT EXISTS idx_federation_catalog_items_peer_project
    ON federation_catalog_items (peer_id, project_name);
CREATE INDEX IF NOT EXISTS idx_federation_catalog_items_updated_at
    ON federation_catalog_items (updated_at);

-- Volltextsuche über den Titel. External Content, damit ON DELETE CASCADE auf
-- federation_catalog_items keine verwaisten FTS-Zeilen hinterlässt.
CREATE VIRTUAL TABLE IF NOT EXISTS federation_catalog_fts USING fts5(
    title,
    content='federation_catalog_items',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS federation_catalog_items_ai
AFTER INSERT ON federation_catalog_items
BEGIN
    INSERT INTO federation_catalog_fts (rowid, title) VALUES (new.rowid, new.title);
END;

CREATE TRIGGER IF NOT EXISTS federation_catalog_items_ad
AFTER DELETE ON federation_catalog_items
BEGIN
    INSERT INTO federation_catalog_fts (federation_catalog_fts, rowid, title)
        VALUES ('delete', old.rowid, old.title);
END;

CREATE TRIGGER IF NOT EXISTS federation_catalog_items_au
AFTER UPDATE OF title ON federation_catalog_items
BEGIN
    INSERT INTO federation_catalog_fts (federation_catalog_fts, rowid, title)
        VALUES ('delete', old.rowid, old.title);
    INSERT INTO federation_catalog_fts (rowid, title) VALUES (new.rowid, new.title);
END;

-- Vom Hub verworfene Einträge, damit der stündliche Abgleich sie nicht immer
-- wieder anfordert.
CREATE TABLE IF NOT EXISTS federation_catalog_rejected (
    peer_id     TEXT NOT NULL REFERENCES federation_peers(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    updated_at  TEXT,
    reason      TEXT,
    PRIMARY KEY (peer_id, kind, item_id)
);

-- Status je Quelle (Client) auf dem Hub.
CREATE TABLE IF NOT EXISTS federation_catalog_sources (
    peer_id           TEXT PRIMARY KEY REFERENCES federation_peers(id) ON DELETE CASCADE,
    last_seq          INTEGER NOT NULL DEFAULT 0,
    interval_seconds  INTEGER,
    last_push_at      TEXT,
    last_full_at      TEXT,
    item_count        INTEGER NOT NULL DEFAULT 0
);

-- Erweiterung federation_peers — erst hier, ganz am Ende (siehe Begründung oben).
ALTER TABLE federation_peers ADD COLUMN is_hub INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_peers ADD COLUMN catalog_accept INTEGER NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_federation_peers_single_hub
    ON federation_peers (is_hub) WHERE is_hub = 1;

COMMIT;
