-- Federation: per-workstation TLS-verify toggle.
--
-- Real-world need: a freshly --tls-auto'd ProjektX serves a self-
-- signed cert for CN=localhost. When we reach it via its Tailscale
-- IP (100.x.y.z), httpx's default cert-verify rejects the chain.
-- For LAN/Tailnet workstations that's totally fine to skip; for a
-- production peer over the public internet we still want to verify.
-- So we make it per-row, with safe default (1 = verify).
ALTER TABLE federation_workstations ADD COLUMN verify_tls INTEGER NOT NULL DEFAULT 1;
