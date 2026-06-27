-- 030: SMB/CIFS-Mounts — externe Fileserver-Freigaben als Projekt-Ressource.
--
-- Gehören dem User (owner), können 0 oder 1 Projekt zugewiesen werden — analog
-- zu VMs/Containern (siehe 005_project_assignments.sql). Beim Projekt-Löschen
-- wird project_id auf NULL gesetzt (kein CASCADE), die Mount-Definition bleibt
-- dem User erhalten.
--
-- Das Passwort wird NICHT hier gespeichert, sondern als Referenz auf ein
-- 'basic'-Credential (Spalte credential) des Owners. mount_state ist der zuletzt
-- gemessene Mount-Zustand.

CREATE TABLE smb_mounts (
    mount_id        TEXT PRIMARY KEY,
    owner           TEXT NOT NULL,
    name            TEXT NOT NULL,
    host            TEXT NOT NULL,
    share           TEXT NOT NULL,
    subpath         TEXT,
    credential      TEXT,
    read_only       INTEGER NOT NULL DEFAULT 0,
    options         TEXT,
    project_id      TEXT,
    mount_state     TEXT NOT NULL DEFAULT 'unmounted',
    last_error_code TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX idx_smb_mounts_project ON smb_mounts(project_id);
CREATE INDEX idx_smb_mounts_owner   ON smb_mounts(owner);
