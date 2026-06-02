# Feature Map: Butler — Visueller Flow-Builder / Automation

> **Modul:** `core/src/hydrahive/butler/`  
> **Frontend:** `frontend/src/features/butler/`  
> **Was:** No-Code Automations. Trigger → Condition → Action. Visuell per Drag & Drop.  
> **Warum:** Ermöglicht komplexe Automations ohne Code — WhatsApp-Nachricht eingeht → Agent antwortet.

---

## Backend-Dateien

| Datei | Verantwortung |
|---|---|
| `models.py` | Pydantic-Modelle: `ButlerRule`, `Trigger`, `Condition`, `Action` |
| `persistence.py` | Rules laden/speichern (JSON-Datei pro User) |
| `dispatch.py` | `dispatch(event)` — prüft alle Rules gegen eingehendes Event |
| `executor.py` | `execute(rule, event)` — führt Actions einer Rule aus |
| `template.py` | Jinja2-Template-Rendering für Action-Parameter |

### Trigger-Implementierungen (`registry/triggers/`)

| Datei | Trigger | Beschreibung |
|---|---|---|
| `message_received.py` | `message_received` | Eingehende Messenger-Nachricht (WhatsApp, Discord) |
| `email_received.py` | `email_received` | Eingehende E-Mail via IMAP |
| `webhook_received.py` | `webhook_received` | HTTP-Webhook (POST an `/api/webhooks/<token>`) |
| `cron_fired.py` | `cron_fired` | Zeitgesteuerter Trigger (Cron-Ausdruck) |
| `git_event_received.py` | `git_event_received` | Git-Event (Push, PR, Issue) |

### Condition-Implementierungen (`registry/conditions/`)

| Datei | Condition | Beschreibung |
|---|---|---|
| `message_contains.py` | `message_contains` | Nachricht enthält Text/Regex |
| `regex_match.py` | `regex_match` | Regex-Match auf beliebiges Feld |
| `contact_in_list.py` | `contact_in_list` | Absender in definierter Liste |
| `time_window.py` | `time_window` | Aktiv nur in bestimmten Uhrzeiten |
| `day_of_week.py` | `day_of_week` | Aktiv nur an bestimmten Wochentagen |
| `payload_field.py` | `payload_field` | Beliebiges Payload-Feld hat Wert |

### Action-Implementierungen (`registry/actions/`)

| Datei | Action | Beschreibung |
|---|---|---|
| `agent_reply.py` | `agent_reply` | Agent mit Nachricht beauftragen, Antwort zurückschicken |
| `reply_fixed.py` | `reply_fixed` | Feste Text-Antwort zurückschicken |
| `send_email.py` | `send_email` | E-Mail versenden |
| `http_post.py` | `http_post` | HTTP POST an externe URL |
| `discord_post.py` | `discord_post` | Nachricht in Discord-Channel posten |
| `git.py` | `git_action` | Git-Operation ausführen (commit, push, ...) |
| `ignore.py` | `ignore` | Nichts tun (für Testing) |
| `_stub.py` | Stub | Basis-Klasse für neue Actions |

---

## Frontend-Dateien

| Datei | Verantwortung |
|---|---|
| `ButlerPage.tsx` | Hauptseite. React Flow Canvas + Palette + Properties. |
| `_ButlerCanvas.tsx` | React Flow Canvas — Nodes und Edges rendern/bearbeiten |
| `NodePalette.tsx` | Drag-and-Drop-Palette mit allen Trigger/Condition/Action-Nodes |
| `nodes.tsx` | Node-Komponenten für React Flow |
| `palette-data.ts` | Alle verfügbaren Nodes mit Labels und Icons |
| `PropertiesPanel.tsx` | Rechte Sidebar: Properties des selektierten Nodes |
| `properties/_triggers.tsx` | Trigger-spezifische Property-Formulare |
| `properties/_conditions.tsx` | Condition-spezifische Property-Formulare |
| `properties/_actions.tsx` | Action-spezifische Property-Formulare |
| `properties/_webhook.tsx` | Webhook-spezifische Properties |
| `properties/_helpers.tsx` | Shared Property-Hilfskomponenten |
| `properties/registry.tsx` | Mapping: Node-Typ → Property-Komponente |
| `useButlerFlow.ts` | State-Hook: Flow-State, Save, Load |
| `adapter.ts` | Konvertierung: Backend-Rule ↔ React-Flow-Graph |
| `types.ts` | TypeScript-Typen |
| `paramSummary.ts` | Kurz-Zusammenfassung eines Nodes für Canvas-Label |
| `_ButlerTopBar.tsx` | Topbar: Save-Button, Rule-Name, Enable/Disable |

---

## Datenfluss: Neue Nachricht kommt an

```
WhatsApp-Nachricht eingeht
  → communication/router.py
  → butler/dispatch.dispatch(event={type: "message_received", from: "+49...", text: "Hallo"})
    │
    ├── Alle Rules des Users laden
    ├── Für jede Rule:
    │   ├── Trigger matcht? (message_received + gleicher Kanal?)
    │   ├── Alle Conditions erfüllt? (message_contains "Hallo"?)
    │   └── Falls ja: executor.execute(rule, event)
    │       └── Actions ausführen (agent_reply → Runner → Antwort zurückschicken)
```

---

## Rule-Datenstruktur (vereinfacht)

```json
{
  "id": "uuid",
  "name": "WhatsApp Begrüßung",
  "enabled": true,
  "trigger": {
    "type": "message_received",
    "channel": "whatsapp"
  },
  "conditions": [
    {
      "type": "message_contains",
      "text": "Hallo",
      "case_sensitive": false
    }
  ],
  "actions": [
    {
      "type": "agent_reply",
      "agent_id": "uuid-des-agents",
      "reply_to_sender": true
    }
  ]
}
```

---

## Template-System

Actions können Jinja2-Templates nutzen:
```
"text": "Hallo {{ event.sender_name }}! Du hast geschrieben: {{ event.text }}"
```
Verfügbare Variablen: `event.*` (alle Felder des eingehenden Events)

---

## Verwandte Subsysteme

- **→ Communication** (`08-communication.md`): Butler bekommt Events von Messenger-Adaptern
- **→ Runner** (`01-runner.md`): `agent_reply` Action ruft Runner auf
- **→ API** (`04-api.md`): `routes/butler.py` — CRUD-Endpoints
