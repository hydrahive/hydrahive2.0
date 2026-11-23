// Ehrlicher Vault-Stand (Vault V1 20.10.2026, Agenten-Etappen 1a/1b 22.11.2026). Nur Aussagen, die im Code belegt sind:
// - PIN-Sperre: core/src/hydrahive/vault/gate.py (423 vault_locked), tokens.py IDLE_SECONDS = 15 * 60,
//   Modul-Tor api/main.py (Manifest "vault": true), Zugangsdaten api/routes/credentials.py
// - Vault-Werkzeuge ALLER Agenten (auch Buddy) nur bei entsperrtem Vault: runner/dispatcher.py → vault/agent_gate.py
//   blocked(); aus Kommunikationskanälen nie (agent_gate.channel_hint). „Jetzt sperren“ sperrt auch Agenten
//   (api/routes/vault.py lock → unlocks.close).
// - Schutzstufen privat/gesundheit: db/_mirror_levels.py, docs/specs/datamining-access.md
// - Außenwirkung: db/_mirror_groups.py OUTWARD_TOOLS
// - Zugangsdaten nie im Klartext an Agenten: credentials/__init__.py (fetch_url-Injection) + Egress-Redaction
export const VAULT_ACTIVE = [
  "Akte, Cryptoboard, Haushaltsbuch, Recht und Zugangsdaten öffnen sich erst nach deiner Vault-PIN. Nach 15 Minuten ohne Nutzung sperrt der Vault wieder.",
  "Auch deine Agenten – dein Buddy eingeschlossen – kommen an Akte, Finanzen und Rechtsfälle nur, solange dein Vault entsperrt ist. „Jetzt sperren“ sperrt sie sofort mit.",
  "Über WhatsApp, Discord, E-Mail und andere Kanäle gibt es nie Vault-Daten – auch nicht bei entsperrtem Vault.",
  "Projekt-Agenten und Spezialisten kommen standardmäßig nicht an Gesundheits- und Privatdaten.",
  "Agenten mit Außenwirkung (Mail, Discord, Shell …) kommen nie an Gesundheits- oder Privatdaten.",
  "Zugangsdaten benutzen Agenten, ohne sie im Klartext zu sehen.",
]

export const VAULT_PLANNED = [
  "Protokoll: wer hat wann die Akte geöffnet, exportiert oder gelöscht.",
  "Buddy-Zugriffe auf sensible Daten im Protokoll sichtbar machen.",
  "Vault-Chat: ein Agent, der die Akte lesen darf, aber nichts nach außen schicken kann.",
  "Befunde als PDF oder Foto hochladen und durchsuchen.",
]
