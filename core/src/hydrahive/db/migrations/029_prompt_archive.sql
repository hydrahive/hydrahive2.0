-- Prompt-Archiv (Prompt Library): wertvolle Generierungs-Prompts als volles
-- "Rezept" pro User speichern, kategorisieren, teilen. Erreichbar via Chat-Footer
-- (Frontend) UND Agent-Tools (list_prompts/get_prompt/save_prompt).
--
-- Konsistenz-Hebel für Serien: style_anchor (fester Stil-Block) + sample_path
-- (Referenzbild). seed ist optionales Zukunfts-Feld — GPT-Image/Gemini nutzen
-- es nicht, erst relevant bei Diffusion-Backend (ComfyUI/SD).
CREATE TABLE IF NOT EXISTS prompt_archive (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT 'other',
    prompt        TEXT NOT NULL,
    style_anchor  TEXT,
    model         TEXT,
    params        TEXT,                       -- JSON-Objekt, modellabhängig
    seed          INTEGER,
    tags          TEXT,                       -- JSON-Array
    notes         TEXT,
    sample_path   TEXT,
    is_public     INTEGER NOT NULL DEFAULT 0,
    use_count     INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_prompt_archive_user_cat ON prompt_archive (user_id, category);
CREATE INDEX IF NOT EXISTS idx_prompt_archive_public ON prompt_archive (is_public);
