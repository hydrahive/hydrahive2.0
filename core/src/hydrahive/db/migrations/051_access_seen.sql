-- Freigaben und Gruppen: welche Funktionen der Bootstrap schon kennt
-- (docs/specs/access-groups.md §11). Eine Funktion wird genau einmal nach
-- ihrem Default behandelt, danach nie wieder. So bleiben Änderungen des Admins
-- auch nach einem Neustart erhalten.

CREATE TABLE access_seen_capabilities (
    capability   TEXT PRIMARY KEY,
    default_kind TEXT NOT NULL CHECK (default_kind IN ('everyone', 'admin_only')),
    first_seen   TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
