# Vault: PIN-Sperre, Protokoll und Vault-Chat

Stand: 12.10.2026 · Task `f2b080f6` · Status: **freigegeben (Till, 12.10.2026)**, Fragen §8 beantwortet
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
- **Grundsatz (Antworten §8):** Die PIN schützt das **Ansehen in der Oberfläche**. Alles, was Funktionen im
  Hintergrund brauchen, läuft weiter: der **Buddy** darf seine Werkzeuge immer nutzen, **automatische Importe**
  (Health-Ingest) und die **Benutzung von Zugangsdaten** durch Agenten bleiben offen. Sperrzeit 15 Minuten.

## 4. Vault-PIN und Sperre

### 4.1 Was gesperrt wird
- **Vault-Bereiche** = Module, die im Manifest `"vault": true` setzen (neu, optional), plus die Kern-Seite
  **Zugangsdaten**. Start: `patientenakte`, `cryptoboard`, `haushaltsbuch`.
- Gesperrt werden die **Schnittstellen für die Oberfläche**: Anfragen mit **Login-Token** an
  `/api/modules/<id>/…` bzw. `/api/credentials…` antworten ohne gültige Vault-Entsperrung mit
  `423 vault_locked`. Die Oberfläche zeigt dann den PIN-Dialog.
- Prüfung **serverseitig** am Modul-Tor (`mount_module_routers`, zusätzlich zu `require_capability`) und an den
  Credential-Routen, nicht nur im Browser.
- **Nicht** gesperrt (sonst bricht etwas, §3 Grundsatz):
  - **Importe von außen**, die mit eigenem Schlüssel statt Login kommen (z. B. der Apple-Health-Import mit
    `X-HH-Health-Key`). Sie laufen über die vorhandenen **Geräte-Routen** `/api/module-device/<id>/…`
    (`api/module_devices.py`: Schlüsselprüfung des Moduls + Rate-Limit), nicht unter `/api/modules/…`, und
    sind damit weder vom Login- noch vom Vault-Tor betroffen.
    Befund 12.10.: Der Health-Import liegt heute unter `/api/modules/patientenakte/health-data/ingest` und
    bekommt seit dem Freigabe-Tor (fd6459c8, 29.09.) `401` → seit 30 Tagen keine Health-Daten. Wird vor V1
    getrennt behoben (Umzug auf Geräte-Route).
  - **API-Keys** (`hh_…`, z. B. für Skripte/Kurzbefehle): gelten als Hintergrund-Zugriff, keine PIN.
    Wer einen API-Key hat, hat ihn bewusst angelegt. Jeder Zugriff wird protokolliert (§5).
  - **Agenten-Werkzeuge** (`query_fhir_data`, `query_health_data`, `query_portfolio`, `fetch_url` mit
    Zugangsdaten …): laufen ohne PIN. Wer welche Daten sehen darf, regeln weiter Freigaben und Schutzstufen
    (Projekt-Agenten/Spezialisten standardmäßig ohne Gesundheit/Privat, Außenwirkung höchstens normal).
    Jeder Aufruf eines sensiblen Werkzeugs wird protokolliert (§5).
- Warum so: Die PIN schützt vor jemandem **am entsperrten Gerät** (Hauptfall). Der Buddy bleibt voll nutzbar,
  z. B. „Wie war mein Blutdruck?“ per WhatsApp.

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
- Die Vault-Chat-**Seite** ist Teil des Vault und braucht die PIN wie alle Vault-Bereiche.
- Jeder Werkzeugaufruf erzeugt `agent_read:<werkzeug>` im Protokoll.
- Sitzungen des Vault-Chats tragen Stufe `gesundheit` → andere Agenten finden sie nur mit dieser Freigabe.

## 7. Etappen

| Etappe | Inhalt | Prüfung |
|---|---|---|
| **V1** | PIN setzen/ändern/Reset (selbst + Admin), Entsperren, Vault-Token, 423-Sperre für Vault-Module und Zugangsdaten-Seite, Ausnahmen (`vault_exempt`, API-Keys), Oberfläche (PIN-Dialog, Sperren-Knopf, Restzeit) | TDD, Mutanten, Live: Akte ohne PIN → gesperrt, mit PIN → offen, nach Pause zu; Health-Ingest und Buddy-Werkzeug laufen weiter |
| **V2** | Protokoll schreiben + Ansicht, Aufbewahrung | Einträge für jede Aktion, keine Inhalte im Protokoll |
| **V3** | Agenten-Zugriffe auf sensible Werkzeuge protokollieren (keine Sperre, Grundsatz §3) | Buddy fragt Akte bei gesperrtem Vault → Antwort kommt, Eintrag `agent_read:query_fhir_data` im Protokoll |
| **V4** | Vault-Chat | Werkzeugliste fest, Außenwirkung unmöglich, Protokoll |
| später | Dokumente (PDF/Foto, OCR, Suche) | eigene Spec |

## 8. Entscheidungen zu den offenen Fragen (Till, 12.10.2026)

1. **Buddy bei gesperrtem Vault:** „Alles, was die Funktion braucht, muss Buddy dürfen.“ → Agenten-Werkzeuge
   werden nicht an die PIN gebunden, nur protokolliert (§4.1, V3).
2. **Zugangsdaten hinter die PIN:** „Wenn es nicht stört und dennoch alles geht, dann ja.“ → Die **Seite**
   Zugangsdaten (ansehen, bearbeiten) ist gesperrt; die **Benutzung** durch Agenten, Webmin, SMB-Mounts usw.
   bleibt offen.
3. **Sperrzeit:** 15 Minuten Standard, ok.

## 9. Nicht in dieser Spec

- Verschlüsselung der Daten auf der Platte mit der PIN (Schlüssel aus der PIN ableiten). Das wäre echter
  Schutz auch gegen Server-Zugriff, macht aber den Reset unmöglich ohne Datenverlust. Bewusst nicht jetzt.
- Teilen von Vault-Bereichen in der Familie (`active_vault_scope` privat/Familie/Geschäft bleibt ungenutzt).
- Hardware-Schlüssel / Passkeys.
