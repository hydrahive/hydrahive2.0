# Plan: Vault V1 – PIN, Entsperren, Sperre (docs/specs/vault.md §4)

## Ziel
Nach V1: Vault-Bereiche (Module mit `"vault": true` + Seite Zugangsdaten) sind in der Oberfläche erst nach
Vault-PIN sichtbar; nach 15 min Pause wieder gesperrt; PIN-Reset selbst (Login-Passwort) und durch Admin.
Agenten-Werkzeuge, API-Keys und Geräte-Routen laufen unverändert weiter.

## Dateien
- `core/src/hydrahive/db/migrations/055_vault.sql` — Tabelle `vault_pins (user_id PK, pin_hash, created_at, updated_at, generation)`
- `core/src/hydrahive/vault/__init__.py` — öffentliche API
- `core/src/hydrahive/vault/pins.py` — PIN setzen/prüfen/zurücksetzen (bcrypt), generation zählt hoch (Tokens ungültig)
- `core/src/hydrahive/vault/tokens.py` — Vault-Token: signiert (secret_key), `uid`, `gen`, `iat`, `last` – gleitend 15 min, max 8 h
- `core/src/hydrahive/vault/lockout.py` — 5 Fehlversuche / 15 min je Nutzer (wie api/middleware/lockout.py)
- `core/src/hydrahive/vault/gate.py` — Dependency `require_vault_unlocked`: nur für Login-Token (kein API-Key), prüft `X-HH-Vault`, sonst 423
- `core/src/hydrahive/api/routes/vault.py` — `GET /api/vault/status`, `POST /setup` (Passwort + PIN), `/unlock`, `/lock`, `/reset` (Passwort + neue PIN), `POST /api/vault/admin/reset/{user_id}` (Admin)
- `core/src/hydrahive/modules/manifest.py` — Feld `vault: bool`
- `core/src/hydrahive/api/main.py` — Modul-Tor: bei `manifest.vault` zusätzlich `require_vault_unlocked`
- `core/src/hydrahive/api/routes/credentials.py` — Router-Dependency `require_vault_unlocked`
- Frontend: `features/vault/` (api.ts, useVault.ts, VaultPinDialog.tsx, VaultGate.tsx), `shared/api-client.ts` (Header `X-HH-Vault`, 423 → Dialog), Vault-Cockpit: Sperren-Knopf + Restzeit
- Module: `patientenakte`, `cryptoboard`, `haushaltsbuch` → `"vault": true` (eigener Modul-PR nach Kern-Merge)
- Tests: `core/tests/test_vault_*.py`, vitest für useVault/api-client

## Reihenfolge (TDD)
1. pins.py + Migration → `test_vault_pins.py` (setzen, prüfen, falsche PIN, Format 6–12 Ziffern, Hash nie Klartext, Reset erhöht generation)
2. tokens.py → `test_vault_tokens.py` (gültig, abgelaufen nach Pause, max 8 h, falscher Nutzer, alte generation ungültig, manipuliert)
3. lockout.py → `test_vault_lockout.py`
4. gate.py → `test_vault_gate.py` (Login-Token ohne Vault → 423; mit gültigem → ok; API-Key → ok ohne Vault; Nicht-Vault-Modul unberührt)
5. routes → `test_vault_routes.py` (setup nur mit richtigem Passwort; unlock/lock; reset; Admin-Reset kennt PIN nicht, Nutzer muss neu setzen; Fehlversuche 429)
6. Manifest-Feld + Modul-Tor + Credentials → `test_vault_module_gate.py` (Fake-Modul mit vault:true)
7. Frontend + vitest, Browser-Rundlauf mit Vite gegen Testserver
8. Mutanten, ruff, volle Suite, Modul-PR (vault:true)

## Akzeptanz
- Akte ohne PIN → PIN-Dialog; mit PIN → offen; nach 15 min Pause wieder Dialog
- Falsche PIN 5× → 15 min Pause
- PIN vergessen → mit Login-Passwort neue PIN, alte Entsperrungen ungültig
- Admin-Reset → Nutzer vergibt beim nächsten Öffnen neue PIN, Admin sieht nie eine PIN
- Buddy-Werkzeug `query_fhir_data` und API-Key-Zugriff laufen bei gesperrtem Vault weiter
- Nicht-Vault-Module unverändert

## Nicht in V1
Protokoll (V2), Protokollierung der Agenten-Zugriffe (V3), Vault-Chat (V4), Dokumente.
