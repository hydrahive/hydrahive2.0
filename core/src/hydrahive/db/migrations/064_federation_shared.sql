-- Gemeinsame Taskpflege (docs/specs/federation-shared-tasks.md §Datenmodell).
-- Etappe G2, Teilstück V1: nur Datenmodell + Hub-Buchführung, noch keine
-- Verteilung (catalog_pull folgt in V2). Tabellen für spätere Teile
-- (Bearbeiten/Warteschlange: federation_catalog_outbox,
-- federation_catalog_applied_ops; Projektzuordnung:
-- federation_catalog_project_map) werden hier bewusst NICHT angelegt.
--
-- Reihenfolge wie 062/063: erst alle CREATE TABLE/INDEX IF NOT EXISTS, dann
-- ganz am Ende alle ALTER TABLE ADD COLUMN, danach das Backfill. Grund (siehe
-- 062): db/migrations.py:46-52 behandelt "duplicate column name"/"already
-- exists" als "Migration schon vollständig angewendet" und markiert sie als
-- erledigt, ohne den Rest des Skripts noch einmal zu laufen. Ein ALTER mitten
-- im Skript würde die danach folgenden CREATE/Backfill-Schritte bei einem
-- solchen Teil-Rerun also überspringen. Die ganze Migration steht zusätzlich
-- in BEGIN/COMMIT: DDL ist in SQLite transaktional, ein Abbruch zwischen zwei
-- ALTERs (z. B. Stromausfall) hinterlässt dann nichts, und der nächste Start
-- wendet die Migration vollständig an.
BEGIN;

-- Hub: fortlaufende Änderungsnummer (eine Zeile). Startwert 0, wird im
-- Backfill unten ggf. auf den Bestand hochgezogen.
CREATE TABLE IF NOT EXISTS federation_catalog_counter (
    id   INTEGER PRIMARY KEY CHECK (id = 1),
    rev  INTEGER NOT NULL DEFAULT 0
);

-- Hub: kurzes Löschprotokoll für die Verteilung (Spec §Änderungsnummer auf
-- dem Hub). Kein dauerhafter Grabstein im Katalog — nur 7 Tage, siehe Auftrag B
-- (Aufräumen) und §Schalter "Wenn die Sichtbarkeit wegfällt".
CREATE TABLE IF NOT EXISTS federation_catalog_deletions (
    rev         INTEGER PRIMARY KEY,
    origin_fp   TEXT NOT NULL,
    kind        TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    owner       TEXT NOT NULL,
    deleted_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_federation_catalog_deletions_deleted_at
    ON federation_catalog_deletions (deleted_at);

-- Client: Kopie der Hub-Metadaten (Spec §Datenmodell, nur auf Clients
-- genutzt). Wird nie wieder gepusht (liegt im Kern, nicht in den
-- Modultabellen).
CREATE TABLE IF NOT EXISTS federation_catalog_mirror (
    origin_fp     TEXT NOT NULL,
    kind          TEXT NOT NULL,
    item_id       TEXT NOT NULL,
    origin_name   TEXT NOT NULL,
    owner         TEXT NOT NULL,
    title         TEXT NOT NULL,
    status        TEXT NOT NULL,
    priority      TEXT,
    project_id    TEXT,
    project_name  TEXT,
    created_at    TEXT,
    updated_at    TEXT,
    received_at   TEXT NOT NULL,
    PRIMARY KEY (origin_fp, kind, item_id)
);

CREATE INDEX IF NOT EXISTS idx_federation_catalog_mirror_owner_project
    ON federation_catalog_mirror (owner, project_name);
CREATE INDEX IF NOT EXISTS idx_federation_catalog_mirror_owner_status
    ON federation_catalog_mirror (owner, status);

-- Startzeile für den Hub-Zähler. Kein ALTER, daher unproblematisch hier
-- (idempotent, kollidiert nicht mit der "duplicate column name"-Erkennung).
INSERT OR IGNORE INTO federation_catalog_counter (id, rev) VALUES (1, 0);

-- Erweiterungen bestehender Tabellen — erst hier, ganz am Ende (siehe
-- Begründung oben).

-- Client-Seite: Schalter + Pull-Zustand (Spec §Schalter, §Nachricht catalog_pull).
ALTER TABLE federation_catalog_settings ADD COLUMN shared INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_catalog_settings ADD COLUMN remote_edits INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_catalog_settings ADD COLUMN pull_rev INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_catalog_settings ADD COLUMN pull_local_cursor TEXT;
ALTER TABLE federation_catalog_settings ADD COLUMN last_pull_at TEXT;
ALTER TABLE federation_catalog_settings ADD COLUMN last_pull_error TEXT;
ALTER TABLE federation_catalog_settings ADD COLUMN last_full_pull_at TEXT;

-- Hub-Seite: was der Push einer Quelle meldet (Spec §Schalter: "Der Client
-- meldet beide Werte in jedem catalog_push mit ... Der Hub speichert sie in
-- federation_catalog_sources").
ALTER TABLE federation_catalog_sources ADD COLUMN shared INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_catalog_sources ADD COLUMN remote_edits INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_catalog_sources ADD COLUMN pull_users TEXT;
ALTER TABLE federation_catalog_sources ADD COLUMN last_pull_at TEXT;
-- reset_local: Ergänzung zum Datenmodell der Spec (dort nicht aufgeführt),
-- gebraucht für §Schalter "Gegenrichtung ... Der Hub antwortet deshalb beim
-- nächsten catalog_pull jedes Clients einmal mit reset_local: true." Der Hub
-- muss sich je Quelle merken, dass er das beim nächsten Pull dieser Quelle
-- noch schuldet (gesetzt von Auftrag B, wenn eine zuvor ausgeschlossene
-- Bedingung wieder erfüllt wird; danach von der Pull-Route zurückgesetzt).
ALTER TABLE federation_catalog_sources ADD COLUMN reset_local INTEGER NOT NULL DEFAULT 0;

-- Hub-Seite: Änderungsnummer je Eintrag (Spec §Änderungsnummer auf dem Hub).
ALTER TABLE federation_catalog_items ADD COLUMN rev INTEGER NOT NULL DEFAULT 0;

-- Index auf der neuen Spalte — erst jetzt möglich, da sie erst durch das
-- ALTER oben entsteht (gleiches Muster wie der Hub-Unique-Index in 062).
CREATE INDEX IF NOT EXISTS idx_federation_catalog_items_rev
    ON federation_catalog_items (rev);

-- Backfill: bestehende Katalogzeilen (Stand <=063) haben rev=0 (Default).
-- Sie bekommen eine eindeutige rev > 0 nach rowid, sonst würde ein späteres
-- after_rev=0 beim ersten Abholen die Altbestände als "noch nie gesehen"
-- einstufen, sie aber die Bedingung "rev > after_rev" nie erfüllen, weil
-- mehrere Zeilen dieselbe rev=0 trügen. rowid ist je Tabelle eindeutig und
-- >= 1, also reicht eine einfache Übernahme.
UPDATE federation_catalog_items SET rev = rowid WHERE rev = 0;

-- Der Zähler steht danach auf dem höchsten vergebenen Wert, damit der
-- nächste echte Upsert (Auftrag B) keine schon vergebene rev wiederverwendet.
UPDATE federation_catalog_counter
    SET rev = (SELECT COALESCE(MAX(rev), 0) FROM federation_catalog_items)
    WHERE id = 1;

COMMIT;
