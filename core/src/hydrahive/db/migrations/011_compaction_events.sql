-- compaction_events: pro Compaction-Pass eine Zeile
-- Aus Token-Audit #129. Loggt jeden Compact (auch skipped + crashed).
-- Erlaubt retrospektive Analyse: warum wurde nicht compactiert,
-- wie viele Tokens wurden gespart, wie lange dauerte das Summarizen.

CREATE TABLE compaction_events (
    id                          TEXT PRIMARY KEY,
    session_id                  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at                  TEXT NOT NULL,
    -- Identity
    agent_id                    TEXT,
    user_id                     TEXT,
    -- Trigger
    triggered_by                TEXT,           -- 'auto' | 'manual' | 'hook'
    trigger_threshold_pct       INTEGER,
    model                       TEXT,           -- Summarizer-Modell
    source                      TEXT,           -- 'default' | hook-name
    instructions                TEXT,           -- User-Fokus (falls gesetzt)
    tool_result_limit           INTEGER,
    -- Skip-Pfad
    skipped                     INTEGER NOT NULL DEFAULT 0,
    skip_reason                 TEXT,
    skip_reason_params          TEXT,           -- JSON
    -- Mengen
    messages_total              INTEGER,
    messages_visible_before     INTEGER,
    messages_to_summarize       INTEGER,
    messages_kept               INTEGER,
    tokens_before               INTEGER,
    tokens_after_estimate       INTEGER,
    -- Cut-Point
    cut_kept_from_index         INTEGER,
    cut_is_split_turn           INTEGER,
    cut_turn_prefix_count       INTEGER,
    -- Summary
    summary_chars               INTEGER,
    summary_tokens_estimate     INTEGER,
    facts_count                 INTEGER,
    files_extracted_count       INTEGER,
    compaction_message_id       TEXT,           -- pointer auf messages.id (kein FK — Cascade-Sicherheit)
    had_previous_summary        INTEGER,
    -- Outcome
    duration_ms                 INTEGER,
    error                       TEXT
);

CREATE INDEX idx_compaction_events_session  ON compaction_events(session_id);
CREATE INDEX idx_compaction_events_created  ON compaction_events(created_at);
CREATE INDEX idx_compaction_events_agent    ON compaction_events(agent_id);
CREATE INDEX idx_compaction_events_skipped  ON compaction_events(skipped);
