# Feature Map: Team-Chat (Matrix / tuwunel)

Mehr-Parteien-Chat: die User *einer* HydraHive-Instanz chatten in freien Räumen, lokale Agenten sind
pro Raum zuschaltbar und antworten bei Anrede. Substrat = Matrix (Homeserver **tuwunel** als Extension),
**Backend-Bridge + native UI** — das Frontend redet nur die HH-API. Schicht 1 (Intra-Instanz) fertig +
5a Mitglieder-Verwaltung; Schicht 2/3 (Föderation) offen.

Volle Referenz mit `datei:zeile`: [`../27-teamchat.md`](../27-teamchat.md).

## Dateien

| Datei | Rolle |
|-------|-------|
| `settings/_teamchat.py` | `teamchat_enabled` (auto-aktiv wenn Homeserver konfiguriert) + `matrix_*` (File-Fallback) |
| `db/teamchat.py` + `db/migrations/025_teamchat.sql` | identities (Token verschlüsselt) / rooms / room_agents |
| `teamchat/client.py` | matrix-nio/httpx: register (UIAA) / login / build_client |
| `teamchat/identity.py` | `ensure_identity` (Mensch) + `ensure_bot_identity` (Bot, eigener Namensraum), Token-Crypto |
| `teamchat/loop_guard.py` | Sliding-Window-Circuit-Breaker gegen Bot-Echo |
| `teamchat/rooms.py` | create / invite / **kick** / list_members / list_joined_rooms / is_member |
| `teamchat/messages.py` | send + history (m.text) |
| `teamchat/broadcaster.py` | `RoomBroadcaster` (SSE-Fanout pro room_id) |
| `teamchat/agent_bridge.py` | `is_addressed`, `respond_if_addressed` (fire-and-forget), `_run_and_post`, LoopGuard-Singleton |
| `teamchat/agent_membership.py` | Bot in Räume zu-/wegschalten (join/leave + DB) |
| `api/routes/teamchat.py` | `/api/teamchat/*` + Authz-Helfer (member/agent-owner/room-manager/known-user) |
| `extensions/*/tuwunel.*` | Homeserver-Extension (Port 6167, Föderation aus) |
| `frontend/src/features/teamchat/*` | api/types/useTeamchat + TeamchatPage/RoomList/ChatView/AgentPanel |

## Architektur-Garantien

- **Kein Matrix-sync-loop**: Nachricht → `POST /messages` → matrix-send → SSE-Broadcast. Einziger Andockpunkt
  für den Agent-Trigger (`schedule_response`).
- **Ein Bot-Account pro Agent**, eigener Namensraum (`agent:{id}` DB / `agent-{id}` localpart) — kollidiert nie
  mit gleichnamigen Menschen-Usern.
- **Anrede via Text** (`@name`/Vokativ), Agent-Run über `run_agent_for_event` (channel="matrix") mit dem
  **agent-eigenen Modell**; Antwort egress-`scrub`t.

## Echtzeit-Flow

```
Mensch postet → POST /rooms/{id}/messages → room_send → room_broadcaster.broadcast (an ALLE inkl. Absender)
                                                          → SSE → useTeamchat (dedupe via event_id)
             → schedule_response → respond_if_addressed → is_addressed? → LoopGuard → _run_and_post
                                                          → Runner → Bot room_send → broadcast
```

## Authz (Endpoints schreiben in die HH-DB → explizit gegated)

| Aktion | Wer darf |
|--------|----------|
| Raum sehen / streamen | Mitglied (Matrix joined) |
| Agent zu-/wegschalten | Mitglied **und** Agent-Besitzer (Admin-Bypass) |
| Mitglied hinzufügen/entfernen | Raum-Ersteller **oder** Admin; nur echte User; Ersteller nicht kickbar |

## Verwandte Subsysteme

- **Runner** ([`01-runner.md`](../01-runner.md)) — der Agent-Run im Raum ist ein normaler Runner-Lauf.
- **Communication / Agent-Glue** ([`08-communication.md`](08-communication.md)) — `run_agent_for_event`-Muster,
  Sender-Rahmung; teamchat ist channel="matrix".
- **Auth** ([`21-auth-security.md`](21-auth-security.md)) — require_auth/Rollen, Credential-Crypto (Token).
- **Frontend-Chat** ([`19-frontend-chat.md`](19-frontend-chat.md)) — EmoteText/Markdown/SSE-Muster wiederverwendet.
- **AgentLink** ([`14-agentlink.md`](14-agentlink.md)) — getrennter Kanal (Agent↔Agent unsichtbar); teamchat ist
  Mensch+Agent sichtbar im Raum.

## Status / Offen

Schicht 1 + 5a fertig, live verifiziert (Testserver .23). Offen: 5b Raum umbenennen/löschen, 5c privat/offen,
5d Presence; Schicht 2/3 Föderation. Modell-Hinweis: Coder/Billig-Modelle (qwen/jamba) antworten oft leer →
Sonnet-Agenten nutzen.
