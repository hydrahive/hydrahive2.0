-- Föderations-Katalog Etappe 3 (docs/specs/federation-catalog.md §Ablauf 3):
-- "Ändert sich updated_at, wird snapshot_body als veraltet markiert." Der
-- Snapshot selbst bleibt (Anzeige bei Offline-Ursprung, Etappe 4), die Markierung
-- sagt nur, dass er nicht mehr zur aktuellen Fassung passt.
-- Ein einzelnes ALTER: bricht es mit "duplicate column name" ab, ist es schon da.
ALTER TABLE federation_catalog_items ADD COLUMN snapshot_stale INTEGER NOT NULL DEFAULT 0;
