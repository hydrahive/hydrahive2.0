-- Vault-PIN je Nutzer (docs/specs/vault.md §4.2). Nur bcrypt-Hash, nie die PIN.
-- generation zählt bei jeder Änderung/jedem Reset hoch; Vault-Tokens mit älterer generation sind ungültig.
-- Zeile bleibt beim Reset bestehen (pin_hash = NULL), damit die generation nicht zurückfällt.
CREATE TABLE IF NOT EXISTS vault_pins (
    user_id     TEXT PRIMARY KEY,
    pin_hash    TEXT,
    generation  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
