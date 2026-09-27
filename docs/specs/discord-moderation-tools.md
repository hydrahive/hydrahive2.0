# Feature-Spec: Discord-Moderationswerkzeuge für Agenten

> **Status:** Freigegeben (Till, 2026-09-27)
> **Baut auf:** `docs/specs/discord-agent-tools.md` (Lesen/Posten/Antworten/Bearbeiten)
> **Ziel:** Buddy kann freigegebene Foren komplett betreuen — Beiträge markieren,
> schließen, sperren, anpinnen, aufräumen und die Tag-Liste pflegen. Immer nur auf
> Anweisung des Benutzers im Chat.

## 1. Problem

Die Discord-Tools können lesen, posten, antworten und eigene Nachrichten
bearbeiten. Für die Forenpflege fehlt alles, was Discord unter „Threads verwalten“,
„Nachrichten verwalten“ und „Kanäle verwalten“ führt: Status-Tags wie „✅ Gelöst“
setzen (moderierte Tags gehen nur mit „Threads verwalten“), Beiträge schließen oder
sperren, Spam und versehentlich gepostete Secrets entfernen, Tags pflegen.

## 2. Scope

### Tools
| Tool | Zweck | Discord-Recht |
|---|---|---|
| `discord_thread_manage` | Forum-Beitrag: Tags setzen/ergänzen/entfernen, Titel ändern, schließen/öffnen, sperren/entsperren, oben im Forum anheften | Threads verwalten |
| `discord_message_pin` | Nachricht in Beitrag/Textkanal anpinnen oder lösen | Nachrichten anpinnen |
| `discord_delete` | Einzelne Nachricht **oder** ganzen Forum-Beitrag löschen | Nachrichten verwalten bzw. Threads verwalten (eigene Nachrichten ohne Recht) |
| `discord_forum_tags` | Tag-Liste eines Forums: anlegen, umbenennen/ändern, entfernen | Kanäle verwalten |

`discord_channels` zeigt zusätzlich, ob ein Kanal für Moderation freigegeben ist.

### Nicht in Scope
- Nutzer kicken, bannen, Timeout, Rollen, Webhooks, Kanäle anlegen/löschen/umbenennen.
- Automatische Moderation ohne Anweisung (Trigger/Butler).
- Massenlöschen (Bulk-Delete) — Löschen immer einzeln.

## 3. Freigabemodell

- Neue Liste `moderation_channel_ids` in `DiscordConfig`, getrennt von
  `tool_channel_ids`. **Fail-closed:** leer = kein Moderationswerkzeug nutzbar.
- Moderation wirkt nur, wenn der Kanal **zusätzlich** in `tool_channel_ids` steht
  (Moderation setzt Zugriff voraus). Forum-Beiträge erben vom Eltern-Forum.
- Discord-Rechte des Bots werden vorab geprüft und fehlen verständlich gemeldet.

## 4. Sicherheit

- **Löschen braucht die Bestätigung des Benutzers**: Der Runner zeigt für
  `discord_delete` immer das Bestätigungs-Popup (wie beim Harakiri-Schutz für
  `shell_exec`), auch wenn beim Agenten keine allgemeine Tool-Bestätigung aktiv ist.
  Ohne Zustimmung (oder nach Timeout) wird nichts gelöscht.
- Gelöschter Inhalt wird **nicht** in die Tool-Antwort übernommen (er könnte
  genau das Secret sein, das entfernt werden soll) — nur ID, Autor, Zeitpunkt, Länge.
- Titel und Tag-Namen laufen vor dem Senden durch dieselbe Egress-Redaction wie
  Posts (System-/Agent-Secrets, Bot-Token).
- Jede Moderationsaktion erhält einen Audit-Log-Grund `HydraHive-Agent: …`.
- Moderationstools sind in keiner Default-Toolliste; nur registriert, wenn Discord
  aktiv ist, und in `OPTIONAL_TOOLS` toleriert.

## 5. Architektur

```
tools/discord_moderate.py              4 dünne Tool-Hüllen (lazy import)
communication/discord/ops_access.py    + resolve_moderated(), is_moderated()
communication/discord/ops_moderate.py  Beitrag verwalten, anpinnen, löschen
communication/discord/ops_forum_tags.py  Tag-Liste pflegen
communication/discord/config.py        + moderation_channel_ids
runner/_runner_tools.py                discord_delete → immer Bestätigung
api/routes/communication_discord_routes.py  + moderation_channel_ids in GET/PUT
frontend/.../DiscordToolChannels.tsx   + „Moderieren“-Häkchen pro freigegebenem Kanal
```

## 6. Akzeptanzkriterien

- [x] Leere Moderationsfreigabe → Moderationstools lehnen verständlich ab; Lese-/Schreibtools unverändert.
- [x] Moderation nur in Kanälen, die zugleich für Werkzeuge freigegeben sind; Beiträge erben.
- [x] Moderierte Tags („✅ Gelöst“) setzbar, Tags ergänzen/entfernen/ersetzen; max. 5.
- [x] Schließen, Öffnen, Sperren, Entsperren, Anheften, Titel ändern.
- [x] Nachricht anpinnen/lösen.
- [x] Löschen fragt immer nach; Inhalt erscheint nicht in der Antwort; Nachricht und Beitrag löschbar.
- [x] Tag-Liste: anlegen, ändern, entfernen; Limit 20 Tags.
- [x] Fehlende Discord-Rechte werden mit dem Namen des Rechts gemeldet.
- [x] UI: Moderations-Häkchen nur für freigegebene Kanäle; PUT ohne Key löscht nichts.
- [ ] Live-Test in FlowKI Club (nach Deploy).
