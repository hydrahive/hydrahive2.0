-- 002: Communication-Felder in sessions für Channel-getriggerte Conversations.
--
-- Eine eingehende WhatsApp-/Telegram-/Mail-Nachricht von einem bestimmten
-- externen Sender soll dieselbe Session ansprechen damit der Master-Agent
-- den Konversations-Kontext behält.

ALTER TABLE sessions ADD COLUMN channel TEXT;
ALTER TABLE sessions ADD COLUMN external_user_id TEXT;

CREATE INDEX idx_sessions_channel ON sessions(channel, external_user_id, agent_id)
    WHERE channel IS NOT NULL;
