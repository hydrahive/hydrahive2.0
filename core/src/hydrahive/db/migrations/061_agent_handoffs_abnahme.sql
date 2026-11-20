-- Ketten-Anker Etappe 3 (docs/specs/chain-anchor.md): Abnahme-Punkte des eingehenden Auftrags.
-- Der Kern prüft den Bericht dagegen, bevor er „fertig“ meldet (agentlink/acceptance.py).
ALTER TABLE agent_handoffs ADD COLUMN anchor_abnahme TEXT;
