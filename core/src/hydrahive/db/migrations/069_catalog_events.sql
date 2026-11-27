-- Messung des Tool-Katalogs je Sitzung (docs/specs/tool-skill-katalog.md V7/K8, Plan Aufgabe 7).
-- kind: search_tools (find_tools) | search_skills (find_skills) | run (per run_tool erfolgreich benutztes Tool).
-- results: JSON-Liste der gefundenen Namen (nur bei Suchen); tool: Name des benutzten Tools (nur bei run).
-- Keine Fremdschlüssel: die Messung darf nie einen Lauf oder das Löschen einer Sitzung blockieren.
CREATE TABLE IF NOT EXISTS catalog_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    kind        TEXT NOT NULL,
    query       TEXT NOT NULL DEFAULT '',
    results     TEXT NOT NULL DEFAULT '[]',
    tool        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_catalog_events_session ON catalog_events(session_id, id);
