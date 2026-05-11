-- llm_calls: pro LLM-API-Call eine Zeile
-- Aus Token-Audit #129. Erlaubt retrospektive Analyse von Token-Verbrauch,
-- Cache-Hit-Rate, Cost und Performance pro Agent/Session/Modell.

CREATE TABLE llm_calls (
    id                      TEXT PRIMARY KEY,
    session_id              TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at              TEXT NOT NULL,
    -- Identity
    agent_id                TEXT,
    user_id                 TEXT,
    -- Request-Parameter
    provider                TEXT NOT NULL,
    model                   TEXT NOT NULL,
    temperature             REAL,
    max_tokens              INTEGER,
    reasoning_effort        TEXT,
    -- Token-Usage (cache-aware)
    prompt_tokens           INTEGER,
    completion_tokens       INTEGER,
    cache_read_tokens       INTEGER,
    cache_creation_tokens   INTEGER,
    -- Response-Meta
    stop_reason             TEXT,
    -- Timing (Millisekunden)
    ttft_ms                 INTEGER,
    total_ms                INTEGER,
    -- Cost (Mikro-Cents — Integer für Drift-stabile SUM-Queries; 1 Cent = 1000 Micros)
    cost_micros             INTEGER,
    -- Kontext
    turn_in_session         INTEGER
);

CREATE INDEX idx_llm_calls_session ON llm_calls(session_id);
CREATE INDEX idx_llm_calls_created ON llm_calls(created_at);
CREATE INDEX idx_llm_calls_agent   ON llm_calls(agent_id);
CREATE INDEX idx_llm_calls_user    ON llm_calls(user_id);
CREATE INDEX idx_llm_calls_model   ON llm_calls(model);
