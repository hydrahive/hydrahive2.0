-- Ketten-Anker (docs/specs/chain-anchor.md, 20.11.2026): Zieldokument und Originalauftrag
-- des EINGEHENDEN Auftrags je Empfänger-Session. ask_agent im Handoff-Lauf hängt sie an jeden
-- Unterauftrag an (gegen „stille Post“). Text, nicht Hash: die Quelle muss wiederherstellbar sein.
ALTER TABLE agent_handoffs ADD COLUMN anchor_ziel TEXT;
ALTER TABLE agent_handoffs ADD COLUMN anchor_ziel_quelle TEXT;
ALTER TABLE agent_handoffs ADD COLUMN anchor_original TEXT;
