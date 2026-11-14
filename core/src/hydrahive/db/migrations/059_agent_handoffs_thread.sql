-- Plan E6 T4 (agent-templates): Folgeauftrag im selben Vorgang setzt die Sitzung des Spezialisten fort.
-- thread = Hash der Sitzung des Auftraggebers (nie die Sitzungs-ID selbst), NULL bei älteren Handoffs.
ALTER TABLE agent_handoffs ADD COLUMN thread TEXT;
CREATE INDEX IF NOT EXISTS idx_agent_handoffs_thread ON agent_handoffs(thread, from_agent, agent_id);
