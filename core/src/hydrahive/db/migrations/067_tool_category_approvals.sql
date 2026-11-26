-- Vom Admin bestätigte Zuordnungen Tool → Kategorie (Katalog, Spec S2/K12).
-- Das feste Mapping im Kern (catalog/categories.py) gilt ohne Eintrag; ein später zugeordnetes Tool (z. B. Modul-Update)
-- ist sichtbar, aber erst mit einer Zeile hier über ``kategorie:<name>`` frei. Plugin-/MCP-Tools, Tools mit Capability,
-- AUTHORING_TOOLS, ask_agent und Außen-Tools werden beim Auflösen immer ausgeschlossen, auch mit Zeile.
CREATE TABLE IF NOT EXISTS tool_category_approvals (
    category     TEXT NOT NULL,
    tool         TEXT NOT NULL,
    approved_by  TEXT NOT NULL,
    approved_at  TEXT NOT NULL,
    PRIMARY KEY (category, tool)
);
