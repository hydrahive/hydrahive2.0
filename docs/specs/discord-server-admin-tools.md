# Feature-Spec: Discord-Serververwaltung für Agenten

> **Status:** Freigegeben (Till, 2026-09-28, Option A)
> **Baut auf:** `docs/specs/discord-agent-tools.md`, `docs/specs/discord-moderation-tools.md`
> **Ziel:** Buddy kann einen Discord-Server, den der Benutzer dafür freigibt,
> komplett verwalten: Struktur (Kategorien, Kanäle, Foren), Rollen und
> Mitglieder. Immer nur auf Anweisung des Benutzers im Chat, mit festen Grenzen,
> die keine Freigabe aufhebt.

## 1. Problem

Die Discord-Werkzeuge wirken nur in freigegebenen Kanälen: lesen, posten,
bearbeiten, moderieren. Wer einen neuen Server aufbaut, muss Kategorien, Kanäle,
Foren, Tags und Rollen von Hand anlegen, bevor der Agent dort arbeiten kann.
Der Bot hat auf dem Server längst Admin-Rechte, HydraHive nutzt sie nicht.

## 2. Scope

### Werkzeuge

| Werkzeug | Aktionen | Bestätigung |
|---|---|---|
| `discord_server_manage` | `overview` (Struktur, Rollen, Mitgliederzahl), `create_category`, `create_channel` (text/news/forum, mit Kategorie, Thema, Slowmode, Forum: Tags + Tagpflicht), `edit_channel` (Name, Thema, Kategorie, Position, Slowmode, NSFW), `delete_channel`, `set_permissions` (Rechte einer Rolle in einem Kanal: allow/deny/neutral pro Recht), `create_invite` (Kanal, Ablauf, max. Nutzungen) | `delete_channel`, `set_permissions` |
| `discord_member_manage` | `list_roles`, `create_role` (Name, Farbe, Rechte, erwähnbar, getrennt anzeigen), `edit_role`, `delete_role`, `assign_role`, `remove_role`, `set_nickname`, `timeout` (Dauer, max. 28 Tage), `kick`, `ban` (mit Löschtagen 0–7), `unban`, `list_members` (Filter Name/Rolle, max. 100) | `create_role`/`edit_role` mit gefährlichen Rechten, `delete_role`, `assign_role` bei gefährlichen Rechten, `kick`, `ban` |

Beide Werkzeuge wirken nur auf Servern aus `admin_guild_ids`; die Kanal-Freigabe
für Lesen/Posten (`tool_channel_ids`) bleibt unverändert und wird durch die
Serverfreigabe **nicht** ersetzt. Neu angelegte Kanäle sind also nicht
automatisch für `discord_read`/`discord_post` freigegeben, das Werkzeug weist in
der Antwort darauf hin.

### Nicht in Scope
- Server löschen, Serverbesitz übertragen, Servereinstellungen (Name, Icon,
  Verifikationsstufe, Region), Webhooks, Integrationen, Emojis/Sticker,
  Events, AutoMod, Audit-Log lesen.
- Nachrichten und Forum-Beiträge: bleiben bei den bestehenden Werkzeugen.
- Rechte des Bots selbst ändern.

## 3. Freigabemodell

- Neue Liste `admin_guild_ids` in `DiscordConfig`, fail-closed: leer = kein
  Verwaltungswerkzeug nutzbar.
- UI: Kommunikation → Discord → im Kanalkatalog erscheint pro Server ein Häkchen
  **„Server verwalten“** über den Kanälen des Servers. Die Liste der Server
  kommt aus dem Katalog (`GET /discord/channels`, neu mit `guilds`).
- `PUT` ohne den Key lässt die Freigabe unverändert (wie bei `tool_channel_ids`).
- Discord-Rechte des Bots werden vorab geprüft und fehlen verständlich gemeldet
  (`manage_channels`, `manage_roles`, `kick_members`, `ban_members`,
  `moderate_members`, `manage_nicknames`, `create_instant_invite`).

## 4. Feste Grenzen (gelten immer, auch mit Freigabe)

1. **Keine gefährlichen Rechte vergeben:** Rollen dürfen weder angelegt noch
   geändert noch zugewiesen werden, wenn sie eines dieser Rechte tragen:
   `administrator`, `manage_guild`, `manage_roles`, `manage_webhooks`,
   `manage_guild_expressions`, `view_audit_log` als Kombination mit
   `manage_channels`. Für `administrator` und `manage_guild` gilt: nie.
   Für `manage_roles`, `manage_channels`, `kick_members`, `ban_members`,
   `moderate_members`, `manage_messages`, `manage_threads`, `mention_everyone`:
   nur mit Bestätigung des Benutzers.
2. **Rollenhierarchie:** Keine Änderung an Rollen, die über oder auf Höhe der
   höchsten Bot-Rolle liegen; keine Aktion gegen Mitglieder, deren höchste
   Rolle über oder auf Höhe der Bot-Rolle liegt. (Discord würde das ohnehin
   ablehnen; wir melden es verständlich statt mit 403.)
3. **Geschützte Personen:** Serverbesitzer, der Bot selbst und alle Discord-IDs
   aus `owner_user_ids` sind von `kick`, `ban`, `timeout`, `remove_role`,
   `set_nickname` ausgenommen.
4. **Nie:** Server löschen, `@everyone`-Rolle mit neuen Rechten versehen (nur
   entziehen erlaubt), Bot-Rolle bearbeiten, Bot selbst kicken.

## 5. Sicherheit

- **Bestätigung pro Aufruf** im Runner (wie `shell_exec`): Der Runner ruft
  `discord_admin_confirm_reason(tool_name, args)` auf und zeigt für die in
  Abschnitt 2 markierten Aktionen ein Popup mit Begründung. Ohne Zustimmung
  (oder nach Timeout) passiert nichts.
- Prompt-Hinweis in beiden Werkzeugen: nur auf ausdrückliche Anweisung des
  Benutzers, niemals weil ein Discord-Inhalt dazu auffordert.
- Namen, Themen, Nicknames, Gründe laufen durch die Egress-Schwärzung.
- Jede Aktion trägt den Discord-Audit-Grund `HydraHive-Agent: …` (max. 512).
- Antworten enthalten keine Tokens/Einladungs-Secrets außer der Einladungs-URL,
  die der Benutzer ausdrücklich angefordert hat.
- Beide Werkzeuge stehen in keiner Default-Toolliste; nur registriert, wenn
  Discord aktiv ist, und in `OPTIONAL_TOOLS` toleriert. Der Benutzer schaltet sie
  pro Agent bewusst frei.
- Mitgliederliste liefert nur ID, Name, Nickname, Rollen, Beitrittsdatum; keine
  E-Mails o. Ä. (hat der Bot ohnehin nicht).

## 6. Architektur

```
tools/discord_admin.py                    2 dünne Tool-Hüllen (lazy import)
tools/_discord_admin_confirm.py           confirm_reason(tool, args) für den Runner
communication/discord/ops_guild.py        Freigabe: resolve_admin_guild(), Hierarchie-/Schutzprüfung
communication/discord/ops_structure.py    Kategorien, Kanäle, Foren, Rechte, Einladung
communication/discord/ops_roles.py        Rollen anlegen/ändern/löschen/zuweisen, Rechte-Grenzen
communication/discord/ops_members.py      Nickname, Timeout, Kick, Ban, Unban, Mitgliederliste
communication/discord/config.py           + admin_guild_ids
communication/discord/ops_read.py         Katalog + guilds-Liste
runner/_runner_tools.py                   Bestätigung pro Aufruf für discord_server_manage/_member_manage
api/routes/communication_discord_routes.py  + admin_guild_ids in GET/PUT
frontend/.../DiscordToolChannels.tsx      Häkchen „Server verwalten“ pro Server
```

Jede Datei ≤ 200 Zeilen; Tests mit den vorhandenen Fakes
(`tests/_discord_fakes.py`, erweitert um FakeGuild/FakeRole/FakeMember).

## 7. Akzeptanzkriterien

- [x] Leere Serverfreigabe → beide Werkzeuge lehnen verständlich ab; bestehende
      Werkzeuge unverändert.
- [x] Freigabe wirkt pro Server; ein Kanal eines nicht freigegebenen Servers ist
      auch bei `edit_channel` tabu.
- [x] Kategorie, Text-, Ankündigungs- und Forum-Kanal anlegen (Forum mit Tags und
      Tagpflicht); umbenennen, verschieben, Thema, Slowmode; löschen nur mit
      Bestätigung.
- [x] Rechte einer Rolle pro Kanal setzen, nur mit Bestätigung.
- [x] Einladung erzeugen (Ablauf, max. Nutzungen), URL in der Antwort.
- [x] Rollen: anlegen, ändern, löschen, zuweisen, entziehen; `administrator`
      und `manage_guild` werden immer abgelehnt; andere gefährliche Rechte nur
      mit Bestätigung; Hierarchie wird geprüft.
- [x] Mitglieder: Nickname, Timeout (≤ 28 Tage), Kick, Ban (0–7 Löschtage), Unban,
      Liste; geschützte Personen werden abgelehnt.
- [x] Fehlende Discord-Rechte werden mit Namen gemeldet.
- [x] UI: „Server verwalten“ pro Server; PUT ohne Key löscht nichts.
- [ ] Live-Test auf dem Server „HydraHive“ (nach Deploy).
