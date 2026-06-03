# Team-Chat — Schicht 1: Intra-Instanz (Design)

> Status: Entwurf, von Till abgesegnet im Brainstorming 2026-06-03. Noch kein Code.
> Vorstufe zu einem Implementierungsplan (writing-plans).

## Kontext

HydraHive2 kennt heute vier Arten von Kommunikation: Buddy-Chat (Mensch ↔ *einem*
Agenten, 1:1), AgentLink (Agent ↔ Agent, unsichtbar), Channels (externe Leute ↔
Agent über den Butler) und Scratchpad (Mensch → Agent, asynchron). Was fehlt: ein
**gemeinsamer Raum mit mehreren Teilnehmern gleichzeitig**.

Tills Vision (Brain-Dump 2026-06-03): ein Chat, in dem sich die User connecten und
direkt in HydraHive miteinander chatten; perspektivisch über Tailscale auch User
*anderer* HydraHive-Knoten; und Agenten in den laufenden Menschen-Raum zuschaltbar,
um gemeinsam mit ihnen zu arbeiten.

Das ist bewusst in **drei Schichten** zerlegt (Regel #2: eines komplett fertig, dann
das nächste). Dieses Dokument spezifiziert **nur Schicht 1**.

| Schicht | Inhalt | Status |
|---|---|---|
| 1 | Intra-Instanz: eigene User chatten + lokaler Agent zuschaltbar | **dieses Doc** |
| 2 | Föderation: Cross-Node über Tailscale (`@user:knoten`) | später |
| 3 | Fremde Agenten cross-node (Trust/Kosten/Permission-Policy) | später |

## Architektur-Entscheidung

**Substrat = Matrix** (Homeserver: conduwuit/tuwunel). Begründung: Der gefährlichste
Teil der Gesamtvision ist die Föderation (Schicht 2) — verteilte Raum-Mitgliedschaft
über Server-Grenzen, Offline-Knoten, Konfliktauflösung. Matrix hat das mit jahrelang
gehärteter State-Resolution gelöst. Eine eigene Föderation zu stricken wäre genau die
Art unkontrollierter Komplexität, die HydraHive1 zerstört hat. Wir geben den härtesten
Teil an ein erprobtes Protokoll ab.

**Form = Backend-Bridge, native UI.** Matrix lebt ausschließlich im Backend. Das
HH-Frontend bleibt nativ und redet *nur* mit der HH-API; die Bridge übersetzt zu
Matrix. Kein eingebettetes Element, kein Matrix-Client im Browser. (HH1 hatte
`matrix-js-sdk` im Browser *geplant*, aber faktisch genau diese Backend-Bridge
gebaut — `console/package.json` enthält kein Matrix-Paket.)

**Struktur = Homeserver als Extension, Logik im Core (konditional).**
- Der conduwuit/tuwunel-Homeserver wird über HH2s **Extension**-Mechanismus
  installiert (JSON-Manifest + Bash-Script, wie gitea/headscale/ollama). Wer keinen
  Team-Chat will, installiert die Extension nicht → kein Team-Chat. Das ist das
  Opt-out.
- Die Team-Chat-**Logik** ist ein Core-Feature-Modul (`core/src/hydrahive/teamchat/`),
  aber **konditional**: ohne erreichbaren Homeserver ist der Bereich inaktiv
  (Nav-Eintrag weg, API meldet „nicht konfiguriert") — exakt wie Mail ohne Mail-Config
  oder WhatsApp ohne Bridge.
- Ein „Team-Chat als Plugin" ist bewusst verworfen: HH2-Plugins können nur Agent-Tools
  registrieren (`plugins/context.py:22`), kein UI/API/Auth-Feature. Ein Chat-Plugin
  müsste am Plugin-System vorbei in den Core greifen und würde die Regel „Core nie für
  Erweiterungen anfassen" *brechen*.

## Scope

**Drin (Schicht 1):**
- Freie Räume zwischen Usern *einer* Instanz (ad-hoc, Slack-/WhatsApp-Gruppen-artig).
- 1:1-Privatchat als Spezialfall (= Raum mit zwei Mitgliedern).
- Raum anlegen, benennen, Mitglieder einladen/entfernen (nur eigene Instanz-User).
- Nachrichten senden/empfangen in Echtzeit (SSE), inkl. History.
- Lokale Agenten in einen Raum zuschalten; sie antworten **nur bei Anrede** (@mention).
- Loop-Schutz für mehrere Agenten/Echo-Schleifen.

**Nicht drin (spätere Schichten):**
- Föderation / Cross-Node (`allow_federation = false` in Schicht 1).
- Fremde Agenten anderer Knoten.
- Token-für-Token-Streaming der Agent-Antwort in den Raum.
- E2E-Verschlüsselung (lokaler Single-Homeserver, kein dringender Bedarf in Schicht 1).
- Voice/Anrufe, Datei-Upload jenseits dessen, was die bestehende Media-Pipeline kann.

## Komponenten

### Backend (`core/src/hydrahive/teamchat/`)

Regel: ein Modul = eine Verantwortung, je < 200 Zeilen.

| Modul | Verantwortung |
|---|---|
| `client.py` | matrix-nio `AsyncClient`-Wrapper: Login, Sync-Loop, `next_batch`-Persistenz |
| `identity.py` | HH-User ↔ Matrix-Account: Provisioning, Access-Token verschlüsselt speichern/laden |
| `rooms.py` | Raum-Operationen: anlegen, einladen, entfernen, Mitglieder, Liste |
| `messages.py` | Nachricht senden/empfangen, History paginiert holen |
| `agent_bridge.py` | Agent zuschalten/wegschalten, @mention erkennen, Runner triggern, Antwort posten |
| `loop_guard.py` | Circuit-Breaker gegen Echo-Schleifen (portiert aus HH1) |
| `broadcaster.py` | SSE-Fanout an verbundene Frontends (Muster wie Live-Sync/SessionBroadcaster) |

### API (`core/src/hydrahive/api/routes/teamchat.py`, Prefix `/api/teamchat`)

- `GET /rooms` — Räume des Users.
- `POST /rooms` — Raum anlegen (Name, initiale Mitglieder).
- `GET /rooms/{id}/messages` — History (paginiert).
- `POST /rooms/{id}/messages` — Nachricht senden.
- `GET /rooms/{id}/stream` — SSE-Stream neuer Events.
- `POST /rooms/{id}/members` / `DELETE /rooms/{id}/members/{user}` — Mitglieder.
- `POST /rooms/{id}/agents` / `DELETE /rooms/{id}/agents/{agent_id}` — Agent zu-/wegschalten.

Alle Endpoints `require_auth`. Verfügbarkeit konditional: ist kein Homeserver
erreichbar, antworten sie mit klarem „teamchat_not_configured".

### DB (`core/src/hydrahive/db/teamchat.py` + Migration)

- `teamchat_identities` — `user_id` ↔ `mxid`, verschlüsselter `access_token`,
  `device_id`, `next_batch`.
- `teamchat_rooms` — HH-seitige Raum-Metadaten: `room_id` (Matrix), `name`,
  `created_by`, `created_at`. (Mitgliedschaft lebt in Matrix; hier nur, was die
  HH-UI schnell braucht.)
- `teamchat_room_agents` — welcher Agent ist in welchem Raum zugeschaltet, von wem.

### Frontend (`frontend/src/features/teamchat/`)

Feature-Folder (Co-location): `TeamchatPage.tsx`, `RoomList.tsx`, `ChatView.tsx`,
`MemberPanel.tsx`, `AgentAttachButton.tsx`, `useTeamchat.ts`, `api.ts`, `types.ts`.
Native HH-UI, Echtzeit über SSE wie Live-Sync. Nav-Eintrag konditional (nur wenn
Backend `teamchat`-Feature aktiv meldet).

### Extension (`extensions/`)

- `manifests/conduwuit.json` — Extension-Manifest (Kategorie network/tools,
  systemd-Service, Health-Check gegen `/_matrix/client/versions`).
- `install/conduwuit.sh` + `uninstall/conduwuit.sh` — portiert aus HH1
  `installer/modules/04_tuwunel.sh`: GitHub-Release-Download, systemd-Unit,
  `conduwuit.toml` (server_name, port 6167 localhost, `allow_federation = false`,
  Registration-Token).

## Datenfluss

**Mensch sendet:** Frontend → `POST /api/teamchat/rooms/{id}/messages` → `messages.py`
postet als die Matrix-Identität des Users (`identity.py`) → conduwuit → Sync-Event in
`client.py` → `broadcaster.py` → SSE → alle verbundenen Frontends rendern.

**Agent (nur bei Anrede):** Raum-Nachricht → Sync → `agent_bridge.py` prüft, ob ein
zugeschalteter Agent per @mention/Name angesprochen ist → wenn ja: `loop_guard.py`
prüft Circuit-Breaker → bei OK: **HH-Runner**-Run mit Raum-Kontext (wer hat was
gesagt) als Input → Antwort als Bot-Account posten (`messages.py`) → Sync → SSE.
Während der Agent denkt: Typing-Indikator im Raum.

## Schlüssel-Entscheidungen

1. **Identität:** echte Matrix-Accounts pro HH-User (HH1-erprobt), auto-provisioniert
   beim ersten Team-Chat-Zugriff. Nebeneffekt: später optional auch per Element
   nutzbar (HH1-Idee „ein Account, zwei Zugangswege").
2. **Token-Storage:** Access-Tokens verschlüsselt in der HH-DB über den vorhandenen
   `credentials/_crypto`-Layer — **nicht** lose JSON-Dateien wie HH1 (deren
   Schwachstelle).
3. **History:** vorhanden (HH1-Lücke geschlossen) — Matrix speichert ohnehin, Bridge
   holt paginiert über die Client-API.
4. **Kein Token-Streaming im Raum:** Agent-Antwort erscheint als ganze Nachricht +
   Typing-Indikator. Token-für-Token in einen Matrix-Raum bedeutet ständiges
   Edit/Replace — unschön und un-idiomatisch.
5. **Ein Runner-Pfad:** der Agent-Run im Raum nutzt denselben Runner wie der
   Buddy-Chat. `agent_bridge.py` baut nur den Raum-Kontext als Input und postet das
   Ergebnis zurück — keine zweite Agenten-Welt.

## Fehlerbehandlung (an System-Grenzen)

- Homeserver nicht installiert/erreichbar → Feature inaktiv, API `teamchat_not_configured`,
  Frontend zeigt Hinweis „Team-Chat-Extension nicht installiert".
- Matrix-Sync-Fehler → `client.py` reconnectet mit Backoff; SSE-Clients erhalten
  Verbindungsstatus.
- Agent-Run-Fehler → Fehlermeldung als Bot-Nachricht im Raum, kein stiller Abbruch.
- Loop-Guard greift → der Agent schweigt für die Sperrzeit; Ereignis wird geloggt.

## Reuse aus HH1 (`/home/till/octopos`, Vorlage — kein Copy-Paste ohne Verstehen)

- `installer/modules/04_tuwunel.sh` → Extension-Manifest + Install-Script.
- `core/src/hydrahive_core/matrix_agent.py` → matrix-nio-Anbindung, Sync-Loop,
  Account-Login.
- `matrix_agent.py:153–206` → **Loop-Detektion** (Circuit-Breaker: ≥3 Bot-Nachrichten
  schnell hintereinander → 300s Sperre; PingPong-Muster → sofort blocken).
- `core/src/hydrahive_core/provisioner.py:565–688` → Account-Registrierung (UIAA) +
  Raum-Erstellung (Power-Levels, Invites).

## Tests (Regel: 80 % Coverage, TDD)

- `loop_guard`: Circuit-Breaker-Logik (Schwellen, Sperrzeit, PingPong) — reine Unit.
- `agent_bridge`: @mention-Erkennung (angesprochen / nicht angesprochen / mehrere
  Agenten), Runner-Trigger nur bei Anrede.
- `identity`: Provisioning-Lifecycle, Token-Verschlüsselung-Roundtrip.
- `rooms`/`messages`: gegen einen Mock-Homeserver (matrix-nio gegen Fake-Responses).
- API-Routen: Auth, konditionale Verfügbarkeit, Happy-Path Senden/Lesen.

## Detail-Entscheidungen (von Till bestätigt 2026-06-03)

1. **Identitäts-Provisioning: lazy.** Die Matrix-Identität wird beim *ersten*
   Team-Chat-Zugriff eines Users angelegt, nicht beim User-Anlegen — kostet nichts
   für User, die den Chat nie nutzen.
2. **Agent-Anrede: @mention primär, Klartext-Name zusätzlich.** `agent_bridge`
   erkennt eine echte Matrix-`@mention` als primären Trigger und zusätzlich den
   Klartext-Namen/ein Trigger-Wort.
3. **Ein Bot-Account pro zugeschaltetem Agenten** (nicht ein gemeinsamer Bridge-Bot).
   Jeder Agent erscheint im Raum als eigene Identität.
4. **Homeserver = tuwunel** (aktiv gepflegter conduit-Fork), das Extension-Manifest
   aber generisch gehalten, damit ein Wechsel des Forks nicht die Logik berührt.
