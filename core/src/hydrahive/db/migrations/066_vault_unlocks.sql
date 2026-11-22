-- Serverseitiger Entsperr-Zustand des Vaults je Nutzer (Ziel vault-agenten §1.3, Etappe 1a).
-- Gleiche Uhr wie der Vault-Token (vault/tokens.py): offen, solange now - last_used_at <= IDLE_SECONDS und
-- now - unlocked_at <= MAX_SECONDS. generation = PIN-generation beim Entsperren; Sperren/PIN-Wechsel erhöhen
-- sie (vault/pins.py), damit ist eine ältere Zeile sofort ungültig. In der DB, damit Neustart und mehrere
-- Worker denselben Zustand sehen.
CREATE TABLE IF NOT EXISTS vault_unlocks (
    user_id       TEXT PRIMARY KEY,
    unlocked_at   REAL NOT NULL,
    last_used_at  REAL NOT NULL,
    generation    INTEGER NOT NULL
);
