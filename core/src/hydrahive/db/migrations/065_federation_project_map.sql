-- Gemeinsame Taskpflege G3 (docs/specs/federation-shared-tasks.md §Projektzuordnung):
-- manuelle Zuordnung eines Ursprungsprojekts zu einem eigenen Projekt, je Nutzer,
-- und der Stand der Ursprünge auf dem Client (für „nicht aktuell“).
--
-- Die Zuordnung wird beim Lesen berechnet (manuell → gleicher Name → nicht
-- zugeordnet) und NICHT gespeichert. Diese Tabelle hält nur manuelle Korrekturen:
-- ``target`` ist eine lokale ``project_id`` oder ``hidden`` („nicht anzeigen“).
-- „automatisch“ heißt: keine Zeile. Eine manuelle Zuordnung hängt an der
-- ``origin_project_id`` und bleibt deshalb, wenn der Ursprung das Projekt umbenennt.
--
-- Nur CREATE … IF NOT EXISTS, kein ALTER: ein zweiter Lauf ändert nichts
-- (Muster 062–064, ganze Migration in einer Transaktion).
BEGIN;

CREATE TABLE IF NOT EXISTS federation_catalog_project_map (
    username           TEXT NOT NULL,
    origin_fp          TEXT NOT NULL,
    origin_project_id  TEXT NOT NULL,
    target             TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    PRIMARY KEY (username, origin_fp, origin_project_id)
);

-- Client: Stand der Ursprünge laut Hub (``instances`` aus catalog_pull), für
-- ``origin_last_seen``/``stale`` der fremden Einträge (Spec §Kern-Schnittstelle).
CREATE TABLE IF NOT EXISTS federation_catalog_mirror_instances (
    origin_fp    TEXT PRIMARY KEY,
    origin_name  TEXT,
    last_seen    TEXT,
    stale        INTEGER NOT NULL DEFAULT 0,
    received_at  TEXT NOT NULL
);

COMMIT;
