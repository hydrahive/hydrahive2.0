# Feature Map: Communication — WhatsApp, Discord, Mail

> **Modul:** `core/src/hydrahive/communication/`  
> **Was:** Messenger-Adapter. Eingehende Nachrichten → Agent. Ausgehende Antworten → Messenger.  
> **Warum:** HydraHive soll überall erreichbar sein — nicht nur im Web-UI.

---

## Architektur

```
Externe Messenger
    │
    ├── WhatsApp (Baileys JS-Bridge, via eigenem Node-Prozess)
    ├── Discord (discord.py)
    └── E-Mail (IMAP-Poll + SMTP-Send)
    │
    ▼
communication/router.py  ← Zentrale Dispatch-Stelle
    │
    ├── Butler-Dispatch (butler/dispatch.py)
    └── _agent_glue.py → Runner (LLM-Antwort)
    │
    ▼
Adapter.send_reply() → Antwort zurück an Messenger
```

---

## Dateien

### Kern

| Datei | Verantwortung |
|---|---|
| `base.py` | `BaseAdapter` Basisklasse für alle Adapter |
| `registry.py` | Registrierung aller aktiven Adapter |
| `router.py` | Haupt-Dispatch: eingehende Events → Butler + AgentGlue |
| `_session_lookup.py` | Mapping: Messenger-Contact → HH2-Session (persistiert) |
| `_agent_glue.py` | `send_to_agent()` — schickt Nachricht an Runner, Antwort zurück |

### WhatsApp

| Datei | Verantwortung |
|---|---|
| `whatsapp/adapter.py` | WhatsApp-Adapter. Verbindet sich mit Baileys-Bridge via WebSocket. |
| `whatsapp/config.py` | WhatsApp-Konfiguration (Telefonnummer, QR-Code-Status, Agent-Zuweisung) |
| `whatsapp/filter.py` | Nachrichten-Filter (Gruppen ignorieren, Spam-Schutz, Allowlist/Blocklist) |
| `whatsapp/process.py` | Nachrichtenverarbeitung (Text, Voice, Bilder, Dateien) |

### Discord

| Datei | Verantwortung |
|---|---|
| `discord/adapter.py` | Discord-Adapter. discord.py Bot. Channels, DMs, Thread-Support. |
| `discord/config.py` | Discord-Konfiguration (Bot-Token, Channel-IDs, Guild-ID) |
| `discord/filter.py` | Filter: welche Channels/User werden verarbeitet |

### E-Mail

| Datei | Verantwortung |
|---|---|
| `mail/imap_poll.py` | IMAP-Polling — regelmäßig neue Mails abrufen |
| `mail/smtp_send.py` | SMTP — E-Mails versenden |
| `mail/watcher.py` | Background-Task: poll in Intervall, neue Mails dispatchen |
| `mail/_seen.py` | Gesehene-Mails-Tracking (verhindert Doppelverarbeitung) |

---

## WhatsApp im Detail

HydraHive nutzt **Baileys** (Node.js-Library) als WhatsApp-Web-Bridge:

```
WhatsApp-Server (offiziell)
    ↕ (WhatsApp Web Protokoll)
Baileys-Bridge (Node.js, läuft als separater Prozess)
    ↕ (WebSocket)
whatsapp/adapter.py (Python)
```

**Wichtig:** Baileys ist inoffiziell — WhatsApp kann Accounts bannen.
Empfohlen: dedizierte SIM-Karte / Business-Account.

**Session-Persistenz:** QR-Code wird einmal gescannt → Auth-Daten in
`/var/lib/hydrahive2/whatsapp/<user>/auth/` gespeichert.

**Voice-Messages:** werden automatisch transkribiert (Wyoming-Whisper STT)
bevor sie an den Agent gehen. Konfigurierbar in WhatsApp-Settings.

**Media-Handling:** Bilder/Dateien werden temporär gespeichert und als
Attachments an den Agent-Context gehängt.

---

## Discord im Detail

- Standard discord.py Bot
- Kann in Channels lauschen (konfiguriert welche)
- Unterstützt DMs
- Threads-Support: pro Conversation einen Thread
- Mention-basiert: Agent antwortet nur wenn @erwähnt (konfigurierbar)
- Rollenfilter: nur bestimmte Discord-Rollen dürfen den Agent nutzen

---

## E-Mail im Detail

- **IMAP** für Empfang (polling, kein Push)
- **SMTP** für Versand
- Credentials aus HH2 Credential-Store
- Betreff-Prefix als Routing-Schlüssel (z.B. `[HH2]` → an Agent weiterleiten)
- Reply-Erkennung: In-Reply-To-Header für Konversations-Threading

---

## Session-Mapping

```
Messenger-Contact → HH2-Session

WhatsApp +4917612345678 → session_id abc123
Discord user:UserName#1234 → session_id def456
Mail from:user@example.com → session_id ghi789
```

- Mapping persistiert in DB (`communication_sessions`-Tabelle)
- Gleicher Contact → immer gleiche Session (Konversations-Kontinuität)
- Über UI konfigurierbar: welcher Agent für welchen Kanal/Contact

---

## Filter & Sicherheit

- **Allowlist**: Nur whitegelistete Contacts können den Agent triggern
- **Blocklist**: Bestimmte Contacts komplett ignorieren
- **Rate-Limiting**: Pro-Contact-Limit (verhindert Spam-Loops)
- **Gruppen-Ignorierung**: Standardmäßig nur DMs, keine Gruppen
- **Butler-First**: Jede eingehende Nachricht geht zuerst durch Butler-Dispatch

---

## _agent_glue.py — der Kleber

```python
async def send_to_agent(
    session_id: str,
    user_input: str,
    adapter: BaseAdapter,
    reply_to: str,  # Contact-ID für Antwort
    *,
    prefix: str | None = None,  # Butler-Prefix (extra_system)
):
    async for event in runner.run(session_id, user_input, extra_system=prefix):
        if isinstance(event, Done):
            await adapter.send_reply(reply_to, event.text)
```

**Bug-Hinweis (bekannt):** Butler-Prefix wird als `extra_system`-Block übergeben.
War früher als User-Message eingefügt (Prompt-Injection-Risiko). Jetzt korrekt
als System-Block.

---

## Verwandte Subsysteme

- **→ Butler** (`07-butler.md`): erhält Events von router.py
- **→ Runner** (`01-runner.md`): _agent_glue ruft runner.run() auf
- **→ Voice** (`29-voice.md`): WhatsApp Voice-Messages → STT
- **→ API** (`04-api.md`): Webhook-Endpoints für eingehende Messages
