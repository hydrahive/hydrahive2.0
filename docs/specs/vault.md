# Vault: PIN-Sperre, Protokoll und Vault-Chat

Stand: 12.10.2026 · Task `f2b080f6` · Status: **Entwurf, wartet auf Freigabe (Till)**
Vorstufe V0 (PR #557): Vault-Cockpit ehrlich gemacht – keine erfundene Sperre mehr, nur echte Bereiche.

## 1. Problem

Gesundheit (Meine Akte), Finanzen (Cryptoboard, Haushaltsbuch) und Zugangsdaten sind heute nur durch den
normalen Login geschützt. Wer an einem entsperrten Rechner sitzt oder ein gültiges Login-Token hat, sieht alles.
Es gibt kein Protokoll, wer wann sensible Daten geöffnet hat, und keinen Agenten, der die Akte lesen darf,
ohne zugleich Mail, Discord oder Shell zu haben.

## 2. Ziel

1. **Vault-PIN:** Sensible Bereiche öffnen sich erst nach einer eigenen PIN. Nach einer Pause sperren sie wieder.
2. **Reset:** Wer die PIN vergisst, kann sie zurücksetzen, ohne dass dabei die Sperre ausgehebelt wird.
3. **Protokoll:** Jede sensible Aktion wird festgehalten und ist für den Nutzer einsehbar.
4. **Vault-Chat:** Ein Agent, der Akte und Finanzen lesen darf, aber keine Werkzeuge mit Außenwirkung hat.

## 3. Entscheidungen (Till, 12.10.2026)

- Eigene **Vault-PIN** statt Login-Passwort. Sie wird beim **ersten Öffnen** vergeben.
- Es muss eine **Reset-Funktion** geben, falls die PIN vergessen wird.
- Reihenfolge: Sperre + Protokoll + Vault-Chat zusammen spezifizieren, in Etappen bauen. Dokumente/OCR später.

## 4. Vault-PIN und Sperre

### 4.1 Was gesperrt wird
- **Vault-Funktionen** = Module, die im Manifest `"vault": true` setzen (neu, optional), plus die Kern-Seite
  Zugangsdaten. Start: `patientenakte`, `cryptoboard`, `haushaltsbuch`.
- Gesperrt heißt: **alle Schnittstellen** dieser Module unter `/api/modules/<id>/…` antworten ohne gültige
  Vault-Entsperrung mit `423 vault_locked`. Die Oberfläche zeigt dann den PIN-Dialog.
- Prüfung **serverseitig** an derselben Stelle wie die Freigaben (`mount_module_routers`), nicht nur im Browser.
- **Agenten-Werkzeuge** mit sensiblen Daten prüfen dieselbe Entsperrung des **Besitzers** (siehe §8 Frage 1).
  Heute (geprüft 12.10.): `query_fhir_data`, `query_health_data` (Akte), `query_portfolio` (Cryptoboard).
  `query_crypto_price` und `query_crypto_analysis` sind öffentliche Kurse → nicht gesperrt. Das Haushaltsbuch hat
  noch keine Agenten-Werkzeuge. Welche Werkzeuge gesperrt sind, kommt aus dem vorhandenen Manifest-Feld
  `sensitive_tools` (Stufe privat/gesundheit), keine zweite Liste.

### 4.2 PIN
- 6–12 Ziffern. Gespeichert nur als **bcrypt-Hash** (wie API-Keys im Kern), nie im Klartext, nie im Log.
- Ablage: `user_preferences` bzw. eigene Tabelle `vault_pins (user_id, pin_hash, created_at, updated_at)`.
- **Erstes Öffnen:** Ist keine PIN gesetzt, verlangt der Vault zuerst das **Login-Passwort** und dann die neue
  PIN (zweimal). So kann niemand mit einem gestohlenen Token eine PIN „für dich“ setzen.

### 4.3 Entsperren
- `POST /api/vault/unlock {pin}` → bei Erfolg ein **Vault-Token**: kurzlebig, an `user_id` und Login-Sitzung
  gebunden, signiert. Er geht als eigener Header mit (`X-HH-Vault`), nicht im Login-Token.
- **Gültigkeit:** gleitend – jede Vault-Anfrage verlängert, nach **15 Minuten Pause** gesperrt (einstellbar
  5–60 min). Harte Obergrenze 8 Stunden.
- **Sperren-Knopf** im Vault-Cockpit und in jedem Vault-Bereich: sofort sperren.
- **Fehlversuche:** 5 falsche PINs in 15 Minuten → 15 Minuten gesperrt (wie `api/middleware/lockout.py`).
  Wird protokolliert.

### 4.4 Reset bei vergessener PIN
- **Selbst:** „PIN vergessen“ → **Login-Passwort** eingeben → neue PIN setzen. Bestehende Vault-Tokens werden
  ungültig. Protokolleintrag „PIN zurückgesetzt“.
- **Durch den Admin:** In der Benutzerverwaltung „Vault-PIN zurücksetzen“. Der Nutzer muss beim nächsten
  Öffnen eine neue PIN vergeben (mit Passwort, §4.2). **Der Admin erfährt die PIN nie und kann keine setzen.**
- Ein Reset löscht **keine Daten**.

## 5. Protokoll

- Tabelle `vault_audit (at, user_id, actor, action, area, detail)`. `actor` = Nutzer oder Agent-ID.
- Aktionen: `unlock`, `unlock_failed`, `lock`, `pin_set`, `pin_reset`, `pin_reset_by_admin`,
  `open:<bereich>`, `export:<bereich>`, `delete:<bereich>`, `agent_read:<werkzeug>`.
- **Keine Inhalte**, nur was, wann, wer, wo (kein Befundtext, keine Beträge).
- Ansicht im Vault-Cockpit: „Letzte Aktivität“ (eigene Einträge). Admins sehen nur, **dass** es Einträge gibt,
  nicht die Gesundheits-Details anderer Nutzer.
- Aufbewahrung: 365 Tage, danach automatisch gelöscht.

## 6. Vault-Chat

- Eigener Agent-Typ-Zusatz `vault: true` am Buddy-Ableger „Vault-Agent“, je Nutzer einmal.
- **Werkzeuge fest:** nur die Werkzeuge aus `sensitive_tools` der Vault-Module (heute `query_fhir_data`,
  `query_health_data`, `query_portfolio`) plus die öffentlichen Kurse und `datamining_*`. **Keine** Werkzeuge mit Außenwirkung (`OUTWARD_TOOLS`), kein
  `shell_exec`, kein `ask_agent`, keine Plugins. Nicht änderbar in der Oberfläche.
- Wissen: `knowledge_access` Bereich „alles des Besitzers“, Stufe **gesundheit**.
- Läuft nur, solange der Vault **entsperrt** ist. Gesperrt → der Chat antwortet „Vault gesperrt“.
- Jeder Werkzeugaufruf erzeugt `agent_read:<werkzeug>` im Protokoll.
- Sitzungen des Vault-Chats tragen Stufe `gesundheit` → andere Agenten finden sie nur mit dieser Freigabe.

## 7. Etappen

| Etappe | Inhalt | Prüfung |
|---|---|---|
| **V1** | PIN setzen/ändern/Reset (selbst + Admin), Entsperren, Vault-Token, 423-Sperre für Vault-Module, Oberfläche (PIN-Dialog, Sperren-Knopf, Restzeit) | TDD, Mutanten, Live: Akte ohne PIN → gesperrt, mit PIN → offen, nach Pause zu |
| **V2** | Protokoll schreiben + Ansicht, Aufbewahrung | Einträge für jede Aktion, keine Inhalte im Protokoll |
| **V3** | Agenten-Werkzeuge der Vault-Module an Entsperrung binden | Buddy fragt Akte bei gesperrtem Vault → klare Meldung, kein Inhalt |
| **V4** | Vault-Chat | Werkzeugliste fest, Außenwirkung unmöglich, Protokoll |
| später | Dokumente (PDF/Foto, OCR, Suche) | eigene Spec |

## 8. Offene Fragen an Till

1. **Agenten bei gesperrtem Vault (V3):** Soll auch der normale **Buddy** Akte/Portfolio nur lesen dürfen, wenn
   der Vault gerade entsperrt ist? (Sicher, aber z. B. eine WhatsApp-Frage „wie war mein Blutdruck?“ geht dann
   nur, wenn du vorher entsperrt hast.) Alternative: Buddy darf weiter, nur andere Agenten nicht.
2. **Zugangsdaten-Seite** auch hinter die PIN, oder nur Akte, Krypto, Haushaltsbuch?
3. **Sperrzeit:** 15 Minuten als Standard ok?

## 9. Nicht in dieser Spec

- Verschlüsselung der Daten auf der Platte mit der PIN (Schlüssel aus der PIN ableiten). Das wäre echter
  Schutz auch gegen Server-Zugriff, macht aber den Reset unmöglich ohne Datenverlust. Bewusst nicht jetzt.
- Teilen von Vault-Bereichen in der Familie (`active_vault_scope` privat/Familie/Geschäft bleibt ungenutzt).
- Hardware-Schlüssel / Passkeys.
