-- 006: Performance-Index für list_for_llm() — filtert häufig nach (session_id, role).
CREATE INDEX IF NOT EXISTS idx_messages_session_role ON messages(session_id, role);
