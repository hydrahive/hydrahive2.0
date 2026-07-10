# Cockpit-Redesign Inventur

Stand: 2026-07-10  
Status: **Abschluss-Inventur nach Etappe Projekt-Cockpit**  
Mockups:

- `generated/mockups/cockpit-v2/index.html`
- `generated/mockups/buddy-page-v1/index.html`
- `generated/mockups/media-cockpit-v1/index.html`
- `generated/mockups/vault-cockpit-v1/index.html`
- `generated/mockups/admin-cockpit-v1/index.html`

## Abschlussstand 2026-07-10

Diese Inventur wurde ursprünglich vor der Umsetzung erstellt und nach der ersten funktionsfähigen Projekt-Cockpit-Etappe aktualisiert.

### Umgesetzt auf `feat/cockpit-redesign`

- Neue Cockpit-Routen sind eingehängt: `/projects`, `/media`, `/vault`, `/admin`.
- Legacy-Layout-Chrome wird auf Cockpit-Routen umgangen; Cockpits verwenden `CockpitShell`.
- Topbar/Quicklinks zeigen die neue Zielstruktur mit `Projekte`, `Buddy`, `Media`, `Vault`, `Admin`.
- Projekt-Cockpit ist produktiv nutzbar:
  - serverseitig persistente aktive Projektwahl über `/api/me/preferences`, inklusive Backend-Test,
  - eingebetteter vollwertiger Chat über `ChatPane`, nicht neu implementiert,
  - Session-Wechsel im Chat-Header als Dropdown statt horizontaler Chip-Leiste,
  - linke Panels für Projekt-Agenten, KI-Einstellungen, Projekt-Git und Workspace-Git,
  - rechte Panels für Git Tree, Workspace-Dateimanager und Projekt-Tasks,
  - einklappbare linke Panels mit serverseitig gespeicherten Cockpit-Preferences,
  - LLM-Auswahl als Dropdown mit Speichern über Agent-API,
  - Workspace-Dateien öffnen, Upload, neue Datei erstellen,
  - Projekt-Tasks listen, erstellen und Status wechseln.
- Testserver `192.168.178.62` läuft auf dem Branch; Tasks-Modul wurde dort als installierter Runtime-Modulstand repariert.
- Frontend-Build war nach den Etappen grün.

### Bewusst noch Platzhalter

- `/media`, `/vault` und `/admin` sind derzeit stabile Cockpit-Einstiegspunkte mit Mockup-/Migrationshinweis, aber noch keine voll ausgebauten Cockpits.
- `/buddy` bleibt die vorhandene Buddy-Seite; das frühere Buddy-Cockpit-Redesign ist separat umgesetzt/gemergt, aber nicht Teil dieser Projekt-Cockpit-Etappe.
- Gitea-Repo-Erstellen/Remote-Anlage ist noch nicht implementiert; nur vorhandene Git-/Repo-Informationen und Pull/Push-Aktionen sind im Projekt-Cockpit sichtbar.
- Agent-Edit-Overlay ist noch nicht umgesetzt; Agentenliste ist aktuell Lesemodus mit Link in die Einstellungen.
- Vault-Sicherheitsmodell, Media-Pipeline und Admin-Konsolidierung bleiben Folgeetappen.

### Merge-Blocker vor `main`

1. Finaler Build/Typecheck auf sauberem Branch.
2. Backend-Tests mindestens für Preferences und betroffene APIs. Hinweis: lokal mit `PYTHONPATH=$PWD/core/src` testen, damit nicht versehentlich das installierte `/opt/hydrahive2`-Paket importiert wird.
3. `hh-review` gegen HydraHive-Architekturregeln.
4. Kurzer UI-Smoke auf Staging: `/projects`, `/media`, `/vault`, `/admin`, Chat senden, Datei-Upload, Datei-Neu, Task-Neu, LLM speichern.
5. Entscheidung, ob Runtime-Modul-Kopie für `tasks` beim Deployment dokumentiert/automatisiert werden muss, damit `/api/modules/tasks/tasks` nicht wieder 404 liefert.

## Ziel

Die neue Hauptstruktur soll vorhandene HydraHive-Funktionen in wenige Cockpits bündeln:

```text
Projekte · Buddy · Media · Vault · Admin · Hilfe
```

Dabei darf keine bestehende Chat-/Tool-/Upload-/Token-/Session-Funktion verloren gehen. Der Umbau muss bestehende Komponenten wiederverwenden, statt Chat und Tooling neu zu bauen.

## Harte Architektur-Regeln

1. **Kein Big-Bang-Replace.** Neue Cockpit-Routen parallel zu bestehenden Seiten bauen.
2. **Chat nicht neu erfinden.** Bestehende Chat-Komponenten kapseln/wiederverwenden.
3. **Globale Persistenz sauber serverseitig.** Kein LocalStorage für zentrale Auswahl wie aktives Projekt.
4. **Gitea = lokales Gitea.** Kein beliebiger Host im Standardflow; lokales Gitea aus System-Konfig/Credential-Store.
5. **Keine versteckten LLM-Calls im Cockpit.** Widgets dürfen nicht automatisch teure Zusammenfassungen/Datamining/Agentenläufe starten.
6. **Uploads/Vibe-Coding überall erhalten.** Jeder Cockpit-Chat ist ein vollwertiger HydraHive-Chat.
7. **Vault/Admin sicher behandeln.** Rechte, Audit, Credential-Redaction und keine Secrets im UI.
8. **PR-Pflicht.** Umsetzung auf Feature-Branch + Pull Request + Review gegen diese Inventur.

---

# 1. Bestehender Chat — Inventur

## 1.1 Komponenten

| Bereich | Bestehende Datei(en) | Muss im neuen Cockpit erhalten bleiben |
|---|---|---|
| Chat-Seite | `frontend/src/features/chat/ChatPage.tsx` | Runtime, Sessionhandling, Send/Cancel, Provider-Struktur |
| Header | `_ChatHeader.tsx` | Session-Titel, Session-ID, Modell, Last-Turn-Tokens, TokenMeter, Compact, NewChat, Orphaned-Banner |
| Nachrichten | `_ChatBubbleThread.tsx`, `_Thread.tsx` | User/Assistant/System, Toolcards, Thinking, Images, Branches, Actions |
| Bubble-Meta | `BubbleMeta.tsx` | Datum/Uhrzeit, Tokens, Cache, Kosten, Modell, Iterationen, Stop-Reason |
| Eingabe | `MessageInput.tsx` | Text, File Upload, Bild Upload, Drag&Drop, Busy/Cancel, Quick Actions |
| Streaming | `_chatStream.ts`, `useChat.ts`, `_assistantRuntime.ts` | SSE/Streaming, Tool-Events, Token-Metadaten, Resend |
| Slash Commands | `commands.ts`, `_SkillCatalogPill.tsx` | `/help`, `/clear`, `/compact`, `/tokens`, `/title`, `/system`, `/tools`, `/agent`, `/export`, `/model`, Skill-Katalog |
| Tool Confirm | `ToolConfirmBanner.tsx` | Freigabe geschützter Tools |
| Tool Cards | `ToolCards.tsx`, `tool_cards/*` | Tool Use/Result, GitDiff, Shell, WebSearch |
| Workspace | `workspace/WorkspacePanel.tsx`, `FileTree.tsx`, `FileOverlay.tsx`, `GitPanel.tsx` | Datei-Browser, Datei-Overlay, Editor, Git-Status/Diff/Stage/Commit |
| Suche | `ChatSearchBar.tsx`, `ChatSearchContext.tsx` | Chat-Suche und aktive Treffer |
| Voice | `useVoiceInput.ts`, `useVoiceOutput.ts` | TTS/Voice, sofern verfügbar |
| Medien | `MediaPreview.tsx`, `ImageLightbox.tsx`, `EpubViewer.tsx` | Bilder, Videos, Audio, EPUB/PDF/Datei-Vorschau soweit vorhanden |
| Kompaktierung | `useChatCompact.ts`, `CompactionBlock.tsx`, `NewChatHint.tsx` | Compact-Flow, Kompaktierungsanzeige, Tokenwarnung |
| Model/Tiefe | `ModelPicker.tsx`, `SessionModelControls.tsx`, `ReasoningEffortPill.tsx` | Modellwahl und Reasoning/Effort |
| Agent Activity | `useAgentActivity.ts`, `AgentPixelMonitor.tsx` | Tool-Fortschritt/Pixelmonitor falls aktiv |

## 1.2 Chat-Funktionen, die nicht verloren gehen dürfen

| Funktion | Bestand | Neue Cockpits |
|---|---|---|
| Session laden/wechseln | vorhanden | Dropdown/Sessionliste pro Cockpit muss dieselbe Session-API nutzen |
| Projektbindung | `session.project_id`, `ProjectPicker`, `NewSessionDialog` | Projekt-Cockpit filtert zwingend nach aktivem Projekt |
| Uploads | `MessageInput` + `chatApi.sendMessage(files)` | in Projekt/Buddy/Media/Vault/Admin vollständig erhalten |
| Bild-Upload | `useChat` erzeugt ImageBlocks | erhalten |
| Drag & Drop | `MessageInput` | erhalten |
| Tool-Calls | ToolCards + Runtime | erhalten |
| Tool-Confirm | `ToolConfirmBanner` | erhalten, besonders Admin/Vault/Git |
| Tokens/Kosten | Header + BubbleMeta | erhalten |
| Cache Read/Create | Header + BubbleMeta | erhalten |
| Compact | Header + slash command | erhalten |
| Model Override | SessionModelControls/ModelPicker | erhalten |
| Reasoning/Tiefe | ReasoningEffortPill | erhalten |
| Retry/Edit/Copy/Raw/TTS | Bubble Thread | erhalten |
| Branch Picker | Assistant UI BranchPicker | erhalten |
| Media Preview | `MediaPreview` | erhalten |
| Datei-Overlay | WorkspacePanel/FileOverlay | erhalten |
| Git Diff/Commit | Workspace GitPanel | erhalten |

## 1.3 Tokenfresser-Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Cockpit lädt Sessionliste/TokenMeter bei jedem Render neu | stabile Hooks, Dependency-Arrays prüfen, Polling vermeiden |
| Datamining-Widgets suchen automatisch breit | nur kleine, gecachte Vorschau; volle Suche erst auf Klick |
| Buddy-Reaction triggert LLM-Zustandsanalyse | keine LLM-Analyse; Zustand aus UI/Event ableiten |
| Media-Cockpit erzeugt automatische Storyboards | nur nach User-Aktion |
| Chat-Komponente doppelt montiert | pro Route nur eine aktive Runtime/Session montieren |
| TokenMeter zu oft refreshen | nur nach Send/Compact/Sessionwechsel |
| Projekt-Cockpit lädt alle Dateien rekursiv | Tree lazy/limitiert laden |

---

# 2. Projekt-Cockpit Inventur

## 2.1 Mockup-Anforderungen

- Topbar: `Projekte · Buddy · Media · Vault · Admin · Hilfe`
- kompaktes Projekt-Dropdown
- Projektwahl global persistent, F5-stabil
- Projekt-Chat in der Mitte
- links: Projekt-Agenten, Git/Gitea, Modell/Tiefe
- rechts: Git Tree, Dateimanager, Projekt-Tasks
- Overlays fixiert, schließen nur über Speichern/Abbrechen
- vollwertiger Chat mit Uploads/Vibe-Coding

## 2.2 Vorhandene Bausteine

| Mockup-Teil | Bestand | Dateien |
|---|---|---|
| Projektliste/Details | vorhanden | `frontend/src/features/projects/api.ts`, `core/src/hydrahive/projects/*` |
| Projekt-Sessions | vorhanden | `frontend/src/features/projects/_SessionsTab.tsx`, Chat Session API |
| Projekt-Agenten/Spezialisten | vorhanden | `_SpecialistsTab.tsx`, Agents API |
| Projekt-Dateien | vorhanden | `_FilesTab.tsx`, WorkspacePanel/FileTree |
| Git-Repos | vorhanden | `_GitTab.tsx`, `_GitRepoCard.tsx`, `core/src/hydrahive/projects/_git*.py` |
| Workspace Git | vorhanden | `frontend/src/features/chat/workspace/GitPanel.tsx`, `core/src/hydrahive/workspace/_git_status.py` |
| Tasks | vorhanden als Modul | `frontend/src/modules/tasks/*` |
| Audit/Notizen/Stats | vorhanden | `_AuditTab.tsx`, `_NotesTab.tsx`, `_StatsTab.tsx` |
| Chat | vorhanden | `frontend/src/features/chat/*` |

## 2.3 Lücken / neu nötig

| Lücke | Aufwand | Notiz |
|---|---:|---|
| Serverpersistente aktive Projektwahl | klein-mittel | User-Preference API nötig, kein LocalStorage |
| Projekt-Cockpit Route/Container | mittel | neue Seite, die vorhandene Panels komponiert |
| Projekt-Task-Kompaktwidget | klein | Task API mit `project_id` filtern/anzeigen |
| Gitea-Status lokal | mittel | lokales Gitea prüfen, Remote anzeigen |
| Gitea-Repo erstellen | mittel-hoch | Credential + API + Rechte + Git remote/push |
| Git Tree kompakt | klein-mittel | aus Git log/status oder bestehendem Panel ableiten |
| Agent-Edit Overlay | mittel | bestehende Agent-Form in Modal nutzen |
| Dateimanager rechts mit Overlay-Editor | klein-mittel | WorkspacePanel/FileOverlay wiederverwenden |

## 2.4 Gitea-Anforderung

- Gitea ist immer das lokal installierte Gitea.
- Gitea-Token kommt aus Credential-Store, nicht aus UI-Eingabe.
- Standardflow:
  1. Projekt-Repo prüfen.
  2. Gitea-Remote vorhanden?
  3. Wenn nein: Button `Repo erstellen`.
  4. Backend erstellt Repo im lokalen Gitea.
  5. Backend fügt Remote `gitea` hinzu.
  6. Optional initial push.
- Rechte: nur Projekt-Admin/Admin.
- Tests: Repo-Erstellung mocken; keine echten Secrets in Logs.

---

# 3. Buddy Inventur

## 3.1 Mockup-Anforderungen

- Buddy bleibt eigener Fun-/Companion-Bereich.
- Topbar gleich.
- links: Reaction-Video Slot, Modus, Stimmung, Quickies, KI-Einstellungen.
- Mitte: Buddy-Chat mit voller Chatfunktionalität.
- rechts: Widgets Musik, Games, Wühlkiste, Scratchpad, kleine Aufgaben, Verknüpfungen.
- Reaction-Videos aus Atelier/Video-Tools.

## 3.2 Vorhandene Bausteine

| Teil | Bestand | Dateien |
|---|---|---|
| Buddy-Seite | vorhanden | `frontend/src/features/buddy/BuddyPage.tsx` |
| Buddy Commands | vorhanden | `features/buddy/commands.ts`, `_BuddyCmdPill.tsx` |
| Buddy Thread | vorhanden | `_BuddyThread.tsx` |
| Buddy Settings | vorhanden | `_BuddySettings*.tsx`, `BuddySettingsPage.tsx` |
| Extensions Panel | vorhanden | `_BuddyExtensionsPanel.tsx` |
| Musik | vorhanden | `modules/musicplayer/MusicPlayerBuddyBox.tsx` |
| Boardgames | vorhanden | `modules/boardgames/components/BoardGamesBuddyBox.tsx` |
| Minigames | vorhanden | `modules/minigames/components/MinigamesBuddyBox.tsx` |
| Scratchpad | vorhanden | `modules/scratchpad/*` |
| Chat-Features | vorhanden | `features/chat/*` |

## 3.3 Lücken / neu nötig

| Lücke | Aufwand | Notiz |
|---|---:|---|
| Reaction-Video Asset Registry | klein-mittel | Mapping reaction→video path/label/triggers |
| Reaction-Video UI | klein | `<video autoplay muted loop playsInline>` |
| Wühlkiste-Widget | klein | zunächst Markdown/Research-Datei anzeigen/verlinken |
| Buddy-Tasks kompakt | klein | bestehendes Tasks-Buddy-Widget prüfen/wiederverwenden |
| Stimmung/Modus sauber speichern | klein-mittel | Buddy prefs ggf. vorhandene Settings erweitern |

---

# 4. Media-Cockpit Inventur

## 4.1 Mockup-Anforderungen

- Media als Produktionscockpit: Idee → Regie → Assets → Clips → Schnitt.
- Projektbindung.
- Media-Projekt Dropdown.
- Modelle: Bild/Video/Musik/Voice.
- Drehbuch/Szenen, Generator-Auftrag, Timeline.
- Asset-Bibliothek.
- Media-Agent Chat.

## 4.2 Vorhandene Bausteine

| Teil | Bestand | Dateien |
|---|---|---|
| Atelier-Hauptmodul | vorhanden | `hydrahive2-modules/atelier/frontend/AtelierPage.tsx` |
| Bildgeneration | vorhanden | `GeneratePanel.tsx`, `backend/generate.py` |
| Video | vorhanden | `VideoGenerationDialog.tsx`, `backend/video.py` |
| Characters | vorhanden | `CharacterLibrary.tsx`, `CharacterReferences.tsx`, `backend/characters.py` |
| Presets/Kamera | vorhanden | `CameraControls.tsx`, `backend/presets.py` |
| Regie/Director | vorhanden | `DirectorPanel.tsx`, `backend/director.py` |
| Screenplay | vorhanden | `backend/screenplay.py`, `tests/test_screenplay.py` |
| Storyboard | vorhanden | `ShotStoryboard.tsx` |
| Audio/Musik | vorhanden | `AudioPanel.tsx`, `AudioLibrary.tsx`, `backend/music.py`, `audio_routes.py` |
| Film Composer | vorhanden | `FilmComposerPanel.tsx`, `backend/film.py` |
| Schnitt | vorhanden/extern | `AtelierCutPanel.tsx`, `hydrahive2-modules/videoeditor/*` |
| Videoeditor | vorhanden | `videoeditor/frontend/*`, `videoeditor/backend/*` |
| Musicplayer | vorhanden | `musicplayer/*` |
| Atelier Buddy Tools | vorhanden | `tools_read.py`, `tools_write.py`, `PLAN-BUDDY-TOOLS.md` |

## 4.3 Lücken / neu nötig

| Lücke | Aufwand | Notiz |
|---|---:|---|
| Media-Cockpit Container | mittel | bestehende Atelier/Videoeditor-Panels einbetten |
| Durchgängige Pipeline-UI | mittel | Status je Projekt/Szene ableiten |
| Media-Projekt Persistenz | mittel | dateibasiert/Atelier-Struktur nutzen |
| Asset-Bibliothek quer über Bild/Video/Audio | mittel | APIs zusammenführen/leichtes Facade-API |
| Media-Agent Chat mit Projekt/Atelier-Kontext | mittel | bestehender Chat + Projekt/Modulkontext |
| Timeline im Cockpit | mittel-hoch | Videoeditor einbetten statt neu bauen |

---

# 5. Vault Inventur

## 5.1 Mockup-Anforderungen

- Vault enthält Medizin, Crypto, Dokumente, Finanzen, private Notizen.
- sensibler Bereich mit Sicherheitsstatus.
- Vault-Chat mit Upload/OCR/Suche.
- letzte Dokumente.
- Datamining für private Historie.

## 5.2 Vorhandene Bausteine

| Teil | Bestand | Dateien |
|---|---|---|
| Patientenakte | vorhanden | `hydrahive2-modules/patientenakte/*` |
| Akte Dashboard/Routes | vorhanden | `patientenakte/frontend/AktePage.tsx`, `AkteSidebar.tsx` |
| FHIR/EGA/Health | vorhanden | `fhir_*`, `ega_*`, `health_*` |
| Akte Tools | vorhanden | `fhir_tool.py`, `health_tool.py` |
| Crypto Board | vorhanden | `hydrahive2-modules/cryptoboard/*` |
| Portfolio/Wallets/Watchlist/Alerts | vorhanden | `cryptoboard/backend/*routes.py`, frontend app |
| Crypto Tools | vorhanden | `crypto_tool.py`, `analysis_tool.py`, `portfolio_tool.py` |
| Scratchpad | vorhanden | `scratchpad/*` |
| Datamining/Memory | vorhanden | `features/datamining/*`, `tools/read_memory.py`, `search_memory.py` |

## 5.3 Lücken / neu nötig

| Lücke | Aufwand | Notiz |
|---|---:|---|
| Vault-Container | mittel | Akte/Crypto/Dokumente in einem Cockpit |
| Vault Lock/Unlock | mittel-hoch | Sicherheitskonzept, Session timeout |
| Dokumenten-Upload/PDF/OCR/FTS | mittel-hoch | existiert als offener Task, nicht fertig |
| Vault Chat Context Guard | mittel | sensible Daten nicht in falsche Projektkontexte leaken |
| Audit sensibler Aktionen | mittel | Akte/Crypto/Dokumente |
| Finanzen/Buchhaltung | hoch/später | bisher nur Idee, kein volles Modul |

## 5.4 Security-Mindestregeln

- Vault-Chat darf sensible Attachments nicht automatisch an normale Projekt-/Buddy-Kontexte weiterreichen.
- Export/Datamining muss bewusst ausgelöst werden.
- Uploads müssen Größen-/Extension-/Path-Guards haben.
- Secrets/Wallet-Daten nicht in Logs, Tool-Outputs oder Bubble-Meta.
- Medizinische Angaben mit klarer Trennung zwischen Akte und Recherche.

---

# 6. Admin Inventur

## 6.1 Mockup-Anforderungen

- User & Rollen
- Module
- Agenten
- Integrationen
- Security
- Systemmetriken
- Logs
- Wartung/Backups
- Admin-Chat

## 6.2 Vorhandene Bausteine

| Teil | Bestand | Dateien |
|---|---|---|
| User | vorhanden | `features/users/*` |
| API Keys | vorhanden | `ApiKeysSection.tsx` |
| System | vorhanden | `features/system/SystemPage.tsx`, Cards |
| Backup | vorhanden | `BackupCard.tsx`, `BackupRestoreModal.tsx` |
| Tailscale | vorhanden | `TailscaleCard.tsx` |
| Samba | vorhanden | `SambaCard.tsx` |
| AgentLink | vorhanden | `AgentLinkCard.tsx` |
| Modules | vorhanden | `features/modules/*` |
| Extensions | vorhanden | `features/extensions/*` |
| Plugins | vorhanden | `features/plugins/*` |
| Credentials | vorhanden | `features/credentials/*` |
| LLM | vorhanden | `features/llm/*` |
| MCP | vorhanden | `features/mcp/*` |
| Skills | vorhanden | `features/skills/*` |
| Settings Hub | vorhanden | `features/settings/*` |

## 6.3 Lücken / neu nötig

| Lücke | Aufwand | Notiz |
|---|---:|---|
| Admin-Cockpit Container | mittel | bestehende Admin-Seiten bündeln |
| Kompakte Logs | mittel | vorhandene Logs/Status APIs prüfen |
| Admin Chat Context | mittel | Chat mit AdminGuard und gefährlichen Tool-Confirmations |
| Rollenmodell final | mittel-hoch | Task „User- & Gruppenmanagement verbessern“ offen |
| Integrationsübersicht | mittel | Credentials/GitHub/Gitea/Tailscale/Webmin zusammenführen |

---

# 7. Topbar und Routen

## 7.1 Neue Zielstruktur

```text
/projects  → Projekt-Cockpit
/buddy     → Buddy
/media     → Media-Cockpit
/vault     → Vault-Cockpit
/admin     → Admin-Cockpit
/help      → Hilfe
```

## 7.2 Alte Routen

Alte Routen bleiben zunächst erhalten und werden intern verlinkt oder später umgeleitet:

```text
/werkstatt
/settings/projects
/settings/agents
/datamining
/memory
/system
/users
/modules
/extensions
/plugins
/credentials
/llm
/mcp
/skills
```

## 7.3 Migration

1. Neue Cockpit-Routen hinzufügen.
2. Topbar auf neue Struktur umstellen.
3. Alte Routen nicht löschen.
4. Cockpits betten bestehende Komponenten ein.
5. Nach Stabilität schrittweise Redirects/Deeplinks prüfen.

---

# 8. Globale Persistenz

## 8.1 Anforderungen

- Aktives Projekt bleibt nach F5 erhalten.
- Idealerweise geräteübergreifend pro User.
- Kein LocalStorage als finale Lösung.

## 8.2 Neue/zu prüfende API

Benötigt wird eine User-Preference-Schicht, z. B.:

```http
GET /api/me/preferences
PATCH /api/me/preferences
```

Mögliche Felder:

```json
{
  "active_project_id": "...",
  "active_media_project_id": "...",
  "active_vault_scope": "private",
  "cockpit_layout": {
    "project": { "leftCollapsed": false, "rightCollapsed": false },
    "buddy": { "widgets": ["music", "games", "scratchpad"] }
  }
}
```

## 8.3 Tests

- Preference wird pro User gespeichert.
- F5 behält aktives Projekt.
- User A sieht nicht User B Auswahl.
- Gelöschtes Projekt führt zu sauberem Fallback.

---

# 9. Inventur-Matrix: Mockup gegen Bestand

| Mockup-Feature | Bestand | Status | Risiko |
|---|---|---|---|
| Topbar neue Sparten | vorhanden | umgesetzt | niedrig |
| Projekt-Dropdown persistent | vorhanden | umgesetzt über `/api/me/preferences` | niedrig |
| Projektchat | vorhanden | umgesetzt via `ChatPane`; Chat nicht neu gebaut | mittel: Regressionen weiter smoke-testen |
| Session-Dropdown im Chat | vorhanden SessionList/API | umgesetzt im kompakten Header | niedrig |
| Kontext/Tokens im Header | vorhanden | erhalten über bestehenden Chat-Header | mittel: UI-Smoke erforderlich |
| Slash-Befehle | vorhanden | erhalten über bestehenden `MessageInput`/Chat-Runtime | niedrig-mittel |
| Upload/Bild/Datei | vorhanden | Chat-Uploads erhalten; Workspace-Upload zusätzlich umgesetzt | niedrig-mittel |
| Agentenliste | vorhanden | kompakt umgesetzt | niedrig |
| Agent-Edit Overlay | vorhanden Formteile | offen; Link zu Einstellungen bleibt | mittel |
| Git Status | vorhanden | Projekt-Git + Workspace-Git eingebunden | niedrig-mittel |
| Gitea Status/Repo erstellen | teilweise | offen/Folgeetappe | hoch/security |
| Dateimanager | vorhanden | umgesetzt mit Öffnen, Upload, neue Datei | niedrig-mittel |
| Git Tree | teilweise | umgesetzt als kompakte Repo-Liste | niedrig |
| Projekt-Tasks | vorhanden Modul | umgesetzt; Runtime-Modul muss installiert sein | mittel: Deployment-Doku |
| Model/Tiefe | vorhanden | Modell-Dropdown umgesetzt; Tiefe bleibt im Chat-Kontext | mittel |
| Buddy Musik/Games | vorhanden | einbetten | niedrig |
| Buddy Reaction Video | neu | leicht | niedrig |
| Wühlkiste Widget | neu/Markdown | leicht | niedrig |
| Media Pipeline | teilweise | Container neu | mittel |
| Atelier Panels | vorhanden | einbetten | mittel |
| Videoeditor Timeline | vorhanden | einbetten | mittel-hoch |
| Vault Akte/Crypto | vorhanden | Container neu | mittel |
| Vault PDF/OCR/FTS | offen | später | mittel-hoch |
| Admin System/User/Module | vorhanden | Container neu | mittel |
| Datamining Widgets | vorhanden API | noch nicht in Cockpit eingebettet | mittel wegen Kosten |

---

# 10. Abschluss-Testmatrix für Merge

Diese Matrix ist der konkrete Smoke-Test vor Merge nach `main`.

| Bereich | Test | Erwartung | Status 2026-07-10 |
|---|---|---|---|
| Routing | `/projects` laden | Cockpit ohne Legacy-Chrome, kein Crash | auf Staging genutzt |
| Routing | `/media`, `/vault`, `/admin` laden | Platzhalter-Cockpits laden; Admin nur mit AdminGuard | noch final smoke-testen |
| Projektwahl | Projekt im Dropdown wechseln, F5 | Auswahl bleibt erhalten | implementiert, noch final smoke-testen |
| Chat | Nachricht im Projekt-Cockpit senden | Bestehende Chat-Runtime streamt, Toolcards/Uploads bleiben verfügbar | noch final smoke-testen |
| Sessions | Session-Dropdown öffnen/wechseln, Session+ | maximal kompakt, kein horizontaler Overflow | umgesetzt, auf Staging geprüft |
| KI-Einstellungen | Modell aus Dropdown wählen und speichern | Agent `llm_model` wird persistiert | umgesetzt, auf Staging geprüft |
| Linke Panels | Panels einklappen, F5 | Collapse-Zustand bleibt erhalten | umgesetzt |
| Projekt-Git | Repos anzeigen, Pull/Push Buttons | vorhandene APIs reagieren; Fehler sichtbar | noch final smoke-testen |
| Workspace-Git | Status/Files anzeigen | bestehendes GitPanel funktioniert im Cockpit | noch final smoke-testen |
| Workspace | Datei öffnen | Overlay/Preview öffnet | auf Staging geprüft |
| Workspace | Upload | Datei landet im aktuellen Ordner und Liste refreshed | auf Staging geprüft |
| Workspace | Neue Datei | Datei wird erstellt und geöffnet | auf Staging geprüft |
| Tasks | Task+ anlegen | Task erscheint im Projektfilter | auf Staging geprüft nach Modul-Reparatur |
| Build | `npm --prefix frontend run build` | Exit 0 | mehrfach grün, vor Merge wiederholen |
| Backend | Preferences-Tests | grün | `PYTHONPATH=$PWD/core/src pytest core/tests/test_me_preferences.py -q` → 6 passed |
| Architektur | `hh-review` | keine Blocker | ausstehend |

# 11. Offene Folgeetappen nach Merge

1. **Media-Cockpit ausbauen:** Atelier/Videoeditor/Pipeline in `/media` einbetten.
2. **Vault-Cockpit ausbauen:** Patientenakte, Crypto, Dokumente, Datamining mit Security-Guard bündeln.
3. **Admin-Cockpit ausbauen:** System/User/Module/Credentials/Logs in `/admin` konsolidieren.
4. **Projekt-Cockpit Gitea-Flow:** lokales Gitea-Repo erstellen, Remote setzen, Initial Push, Rechte/Security-Tests.
5. **Projekt-Cockpit Agent-Edit:** kompakter Edit-Dialog statt nur Einstellungslink.
6. **Deployment-Robustheit Module:** sicherstellen, dass installierte Module wie `tasks` in `/var/lib/hydrahive2/modules` vollständig vorhanden sind oder beim Deploy synchronisiert werden.

---

# 10. Akzeptanzkriterien vor PR-Merge

## 10.1 Allgemein

- [ ] Alle neuen Cockpits sind über Topbar erreichbar.
- [ ] Alte Routen funktionieren weiter.
- [ ] Keine bestehende Chatfunktion fehlt im Projektchat.
- [ ] Upload/Bild/Datei funktioniert im Projektchat.
- [ ] Tool-Confirm funktioniert weiterhin.
- [ ] Token/Kosten/Cache-Meta sichtbar wie vorher.
- [ ] Compact funktioniert.
- [ ] Slash Commands funktionieren.
- [ ] Model/Reasoning-Auswahl funktioniert.
- [ ] Keine unerwarteten LLM-Calls beim reinen Laden der Cockpits.
- [ ] Build/Typecheck grün.

## 10.2 Projekt-Cockpit

- [ ] Aktive Projektwahl serverseitig persistent.
- [ ] F5 behält aktives Projekt.
- [ ] Sessions sind nach Projekt gefiltert.
- [ ] Projekt-Agenten werden angezeigt.
- [ ] Dateien/Workspace sind erreichbar.
- [ ] Git-Status ist sichtbar.
- [ ] Projekt-Tasks sind sichtbar und scrollbar.

## 10.3 Buddy

- [ ] Buddy-Chat bleibt vollwertiger Chat.
- [ ] Musik/Games/Scratchpad Widgets erreichbar.
- [ ] Reaction-Video Slot spielt lokales Video korrekt.
- [ ] Widget-Settings bleiben erhalten.

## 10.4 Media

- [ ] Atelier-Bausteine erreichbar.
- [ ] Projektbindung sichtbar.
- [ ] Keine Generierung startet automatisch.
- [ ] Media-Agent Chat nutzt bestehenden Chat.

## 10.5 Vault

- [ ] Vault-Seite ist klar als sensibel markiert.
- [ ] Keine sensiblen Daten in normale Projektkontexte ohne Useraktion.
- [ ] Akte und Crypto erreichbar.
- [ ] Uploads mit Guards.

## 10.6 Admin

- [ ] AdminGuard schützt Admin-Cockpit.
- [ ] User/System/Module/Credentials erreichbar.
- [ ] Gefährliche Aktionen brauchen Bestätigung.

---

# 11. Empfohlene Implementierungsreihenfolge

## Etappe 0 — Vorbereitung

- [ ] Feature-Branch `feat/cockpit-redesign` erstellen.
- [ ] Diese Inventur im PR verlinken.
- [ ] Tests definieren.

## Etappe 1 — Cockpit-Shell

- [ ] Gemeinsame Cockpit-Komponenten bauen.
- [ ] Neue Topbar-Struktur.
- [ ] Neue Routen als leere/leichte Seiten.
- [ ] Alte Routen unverändert lassen.

## Etappe 2 — Serverseitige Preferences

- [ ] User-Preference API.
- [ ] `active_project_id` speichern.
- [ ] Frontend-Hook `useUserPreferences`.
- [ ] Tests pro User/Fallback.

## Etappe 3 — Projekt-Cockpit MVP

- [ ] Projekt-Dropdown.
- [ ] Bestehenden Chat einbetten.
- [ ] Agentenliste.
- [ ] Workspace/Git/Dateien.
- [ ] Projekt-Tasks.
- [ ] Keine Gitea-Erstellung in dieser Etappe, nur Anzeige wenn Remote vorhanden.

## Etappe 4 — Gitea lokal

- [ ] Lokale Gitea-Konfig/Credential-Auflösung.
- [ ] Repo-Status API.
- [ ] Repo-Erstellen API.
- [ ] Remote hinzufügen/push.
- [ ] Security-Review.

## Etappe 5 — Buddy

- [ ] Buddy in neues Layout.
- [ ] Reaction-Video Registry.
- [ ] Widgets einbetten.

## Etappe 6 — Media

- [ ] Media-Cockpit Container.
- [ ] Atelier Panels einbetten.
- [ ] Videoeditor verlinken/einbetten.

## Etappe 7 — Vault/Admin

- [ ] Vault Container.
- [ ] Admin Container.
- [ ] Guards/Audit prüfen.

---

# 12. Offene Entscheidungen

- Soll `/projects` neue Default-Startseite werden oder bleibt `/buddy` Landing?
- User-Preferences in bestehender User-Tabelle, eigener Datei-Store oder neue DB-Tabelle?
- Gitea Repo-Erstellung: automatisch pro Projekt oder nur manuell per Button?
- Vault Lock: direkt in erster Version oder spätere Sicherheits-Etappe?
- Media-Cockpit als Core-Seite oder Modul-Route?

---

# 13. Verwaltungs-/Einstellungs-Inventur

Diese Einstellungen müssen in den Cockpits weiterhin erreichbar sein. Ziel: keine versteckten alten Settings-Seiten, die man nur kennt, wenn man HydraHive schon versteht.

## 13.1 Agenten-Einstellungen

Quelle: `frontend/src/features/agents/types.ts`, `frontend/src/features/agents/*`

| Gruppe | Felder / Funktionen | Muss erreichbar sein in |
|---|---|---|
| Identität | `name`, `description`, `type`, `domain`, `owner`, `status` | Projekt-Cockpit Agent-Overlay, Admin |
| Modell | `llm_model`, `fallback_models`, Provider/Modellkatalog | Agent-Overlay, Projekt-Chat Einstellungen, Buddy Settings |
| Sampling | `temperature` | Agent-Overlay / Advanced |
| Tokens | `max_tokens`, `thinking_budget` | Agent-Overlay / Advanced |
| Iterationen | `max_iterations` | Agent-Overlay / Advanced, wichtig gegen Tool-Loop/Tokenfresser |
| Tools | `tools`, Tool-Kategorien, Tool-Meta | Agent-Overlay, Admin Tools |
| MCP | `mcp_servers` | Agent-Overlay, Admin/MCP |
| Skills | `disabled_skills`, Projekt-Skills, Agent-Skills | Agent-Overlay, Skills-Admin |
| Kompaktierung | `compact_model`, `compact_tool_result_limit`, `compact_reserve_tokens`, `compact_threshold_pct`, `compact_max_turns` | Agent-Overlay / Compaction Tab, Buddy Settings |
| Tool-Result Limits | `tool_result_max_chars` | Agent-Overlay / Compaction, Token-Schutz |
| Cache | `cache_ttl` (`5m`/`1h`) | Agent-Overlay / Advanced |
| Workspace | `workspace`, Projekt-Workspace-Zuordnung | Projekt-Cockpit |
| Sicherheit | `require_tool_confirm`, Status aktiv/deaktiviert | Agent-Overlay, Admin |
| Memory | `longterm_memory` | Agent-Overlay, Vault/Buddy relevant |
| Mail Tool Config | `tool_config.smtp`, `tool_config.imap`, Passwort gesetzt/maskiert | Agent-Overlay Mail Tab, Buddy Mail Settings |

Pflicht beim Umbau:

- Agentenliste im Projekt-Cockpit darf kompakt sein, aber Klick muss vollständige Verwaltung öffnen.
- Advanced-Felder dürfen eingeklappt sein, aber nicht verschwinden.
- Token-/Iteration-/Compaction-Felder sind kritisch, weil falsche Defaults teuer werden können.

## 13.2 Projekt-Einstellungen

Quelle: `frontend/src/features/projects/types.ts`, `frontend/src/features/projects/api.ts`, `core/src/hydrahive/projects/*`

| Gruppe | Felder / Funktionen | Muss erreichbar sein in |
|---|---|---|
| Basis | `name`, `description`, `notes`, `tags`, `status` | Projekt-Cockpit Einstellungen/Overlay |
| Mitglieder | `members`, später Rollen/Rechte pro Member | Projekt-Cockpit Mitglieder, Admin |
| Projekt-Agent | `agent_id`, Projektagent-Modell bei Erstellung | Projekt-Cockpit |
| Git | `git_initialized`, Repos, Clone, Init, Remote URL, Token, Commit, Push, Pull, Delete | Projekt-Cockpit Git-Block + Detailoverlay |
| Gitea | lokales Gitea Repo Status, Repo erstellen, Remote `gitea`, Push/Pull | Projekt-Cockpit Git/Gitea |
| Serverzuweisung | VMs/Container: `kind`, `id`, `name`, `desired_state`, `actual_state`, CPU/RAM, Image/Disk | Projekt-Cockpit Server/Infra, Admin |
| Mounts | SMB Mounts: Name, Host, Share, Subpath, Credential, Readonly, Options, State/Error | Projekt-Cockpit Dateien/Mounts |
| MCP | `mcp_server_ids` | Projekt-Cockpit Settings |
| Plugins | `allowed_plugins` | Projekt-Cockpit Settings/Admin |
| Spezialisten | `allowed_specialists` | Projekt-Cockpit Agenten |
| LLM/API | `llm_api_key` bzw. projektbezogene Overrides | Projekt-Cockpit Settings, sicher maskiert |
| Sessions | Projekt-Sessions, Status, Titel, updated_at | Projekt-Cockpit Session-Dropdown/Liste |
| Stats | total_sessions, active_sessions, total_messages, total_tokens, last_activity | Projekt-Cockpit Übersicht |
| Audit | `ProjectAuditEntry`, Member/Server/Update Aktionen | Projekt-Cockpit Audit/Admin |
| Butler/Webhooks | Projekt-Webhook URL | Projekt-Cockpit Integrationen |

Pflicht beim Umbau:

- GitHub/Gitea Tokens dürfen nie offen angezeigt werden.
- Serverzuweisung darf nicht aus der UI verschwinden.
- Mounts/Dateien müssen zusammen gedacht werden, sonst findet man Workspace-Daten nicht.
- Projekt-Settings müssen aus dem Cockpit erreichbar sein, nicht nur unter alter Settings-Seite.

## 13.3 Buddy-Einstellungen

Quelle: `frontend/src/features/buddy/api.ts`, `frontend/src/features/buddy/BuddySettingsPage.tsx`

| Gruppe | Felder / Funktionen | Muss erreichbar sein in |
|---|---|---|
| Identität | `name`, `character` | Buddy Settings / Overlay |
| Modell | `model`, verfügbare Modelle, `setModel` | Buddy links unten / Settings |
| Tools | `tools`, `all_tools` | Buddy Settings Tools |
| Sprache | `language`: de/en/auto | Buddy Settings |
| Ton | `tone`: locker/professionell/knapp | Buddy Settings / Modus |
| Kontext | `context` | Buddy Settings Kontext |
| Kompaktierung | `compact_threshold_pct`, `compact_model`, `tool_result_max_chars` | Buddy Settings Compaction |
| Mail | `tool_config.smtp`, `tool_config.imap` | Buddy Settings Mail |
| Session | `session_id`, clear, remember, character reset | Buddy Chat |
| Projektbezug | `project_id` falls gesetzt | Buddy/Projekt-Verknüpfung |
| Widgets | Musik, Games, Scratchpad, Wühlkiste, Reaction Videos | Buddy rechte Seite / Widget Settings |

Neu/noch zu definieren:

- Reaction-Video Registry: `reaction`, `label`, `video_path`, `triggers`, `enabled`.
- Widget-Reihenfolge/Sichtbarkeit serverseitig persistent.
- Buddy-Stimmung/Modus sauber speichern, nicht nur temporär.

## 13.4 Chat-/Session-Einstellungen

| Gruppe | Bestand | Muss erhalten bleiben |
|---|---|---|
| Session | Titel, ID, Status, Agent, Projekt, created/updated | Session-Dropdown, Header, Session-Overlay |
| Modell Override | `session.metadata.model_override` | Chat-Header/Model Controls |
| Reasoning/Tiefe | `reasoning_effort` | Chat Controls |
| System Prompt | Anzeige im Header-Tooltip, `/system` | erhalten |
| Kompaktierung | `/compact`, Compact Button, CompactionBlock | erhalten |
| Token/Kosten | Last Turn + Bubble Footer | erhalten |
| Uploads | Dateien/Bilder/DragDrop | erhalten |
| Vibe Coding | Datei öffnen, Patch, Diff, Tests, Commit über Tools/Workspace | Projekt/Admin/Media/Vault Chats |
| Tool Confirmation | geschützte Tools bestätigen | erhalten, besonders Admin/Vault/Git |
| Slash Commands | help/clear/compact/tokens/title/system/tools/agent/export/model/skill/pixel | erhalten |
| Search | ChatSearch | erhalten oder bewusst später einbauen |
| Branches | BranchPicker | erhalten |
| Voice/TTS | useVoiceOutput/Input | erhalten wo verfügbar |

## 13.5 Tools, Skills, Hooks, Integrationen

| Bereich | Bestand | Cockpit-Ziel |
|---|---|---|
| Agent Tools | Toolliste, Kategorien, enable/disable | Agent-Overlay/Admin |
| MCP Tools | MCP Server und Toollisten | Agent-Overlay/Admin/MCP |
| Skills | globale, projektweite, specialist-spezifische Skills | Projekt-Cockpit Agenten + Admin Skills |
| Butler Hooks | GitHub/Gitea/Webhooks/Projekt-Webhook | Projekt Integrationen + Admin |
| Datamining | Sessions, Semantic, Timeline, Today, Import GitHub/Gitea Issues | Cockpit Widgets + volle Datamining-Seite |
| Memory | read/search/write memory | Buddy/Vault/Projekt-Kontext |
| Credentials | GitHub, Gitea, OpenRouter, Mail, Tailscale etc. | Admin Credentials, maskiert |
| Modules | install/enable/update | Admin Modules, Media/Vault Verknüpfung |
| Extensions | install/run | Admin/Integrationen |
| Plugins | Plugin-Tools | Admin/Agent Tools |

## 13.6 Weitere Punkte, die leicht vergessen werden

- HelpButton/Hilfe-Kontext pro Cockpit.
- i18n Keys für neue Labels.
- Empty States: keine Projekte, keine Sessions, keine Repos, keine Tasks.
- Fehlerzustände: Gitea nicht installiert, Token fehlt, Repo dirty, Mount error.
- Loading/Busy States bei Commit/Push/Pull/Repo erstellen.
- Mobile Layout: Topbar bleibt, Panels werden Drawer/Stack.
- Accessibility: Buttons beschriften, Overlays per ESC? Wenn ESC erlaubt, trotzdem nicht per Außenklick schließen.
- Audit Logs bei sensiblen Änderungen.
- Project/Buddy/Media/Vault/Admin dürfen nicht alle dieselben Daten ungefiltert anzeigen.

---

# 14. Fazit

Das Redesign ist baubar, weil die meisten Systeme bereits existieren. Der Hauptaufwand ist die professionelle Zusammenführung. Kritisch ist nur, den Chat nicht neu zu bauen, keine Verwaltungsfelder zu verlieren und keine versteckten LLM-/Datamining-Kosten zu erzeugen.

Nächster Schritt: Plan aus dieser Inventur ableiten und auf `feat/cockpit-redesign` als kleine Etappen umsetzen.
