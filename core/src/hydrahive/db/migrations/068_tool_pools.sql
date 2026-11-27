-- Freigabe-Pools des Tool-Katalogs (docs/specs/tool-skill-katalog.md E1/E3/E5/S3/S5).
-- owner_tool_grants: was ein Nutzer an SEINE Agenten vergeben darf (vom Admin gesetzt, Standard leer = nichts, E5).
-- agent_tool_pools:  Tools/Kategorien, die diesem Agenten per ask_agent pro Auftrag zugewiesen werden dürfen (E3).
--                    by_admin = ein Admin hat den Eintrag gesetzt (nicht an die Besitzer-Freigabe gebunden, E5).
-- project_tool_pools: schränkt den Pool der Projekt-Agenten nur ein, nie erweitern (S5); leer = keine Einschränkung.
-- tool_or_category: Tool-Name oder ``kategorie:<name>``. Gesetzt wird nur über agents/tool_pools.py.
CREATE TABLE IF NOT EXISTS owner_tool_grants (
    username          TEXT NOT NULL,
    tool_or_category  TEXT NOT NULL,
    granted_by        TEXT NOT NULL DEFAULT '',
    granted_at        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (username, tool_or_category)
);
CREATE TABLE IF NOT EXISTS agent_tool_pools (
    agent_id          TEXT NOT NULL,
    tool_or_category  TEXT NOT NULL,
    by_admin          INTEGER NOT NULL DEFAULT 0,
    set_by            TEXT NOT NULL DEFAULT '',
    set_at            TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (agent_id, tool_or_category)
);
CREATE TABLE IF NOT EXISTS project_tool_pools (
    project_id        TEXT NOT NULL,
    tool_or_category  TEXT NOT NULL,
    set_by            TEXT NOT NULL DEFAULT '',
    set_at            TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (project_id, tool_or_category)
);
