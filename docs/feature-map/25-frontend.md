# Frontend-Shell, Chat & Workspace

> Scope dieser Sektion: die **App-Shell** (Routing, Topbar/Layout, Theme/Glow-Redesign,
> i18n-Verdrahtung, Update/Restart-Modals, Domain-Farben) und das komplette
> **Werkstatt-Chat-Subsystem** (`features/chat/*`) inklusive 3-Panel-Layout,
> Bubble-Thread, MessageInput, Slash-Commands, Hydra-Emotes, Tool-Cards, Media,
> Voice (STT/TTS), Token-Meter, Compaction-UI und das Workspace-Panel
> (FileTree/Monaco/Git/Media-Viewer).
>
> Pfad-Wurzel für alle Datei-Referenzen: `frontend/src/`. Backend-Routen sind mit
> `core/src/hydrahive/api/routes/` angegeben.

---

## WAS

### Routing & App-Bootstrap

- `main.tsx:10` — React-Root-Mount in `#root` unter `<StrictMode>`.
- `main.tsx:3-4` — importiert `./index.css` (Tailwind + Redesign-Layer) und `./i18n` (i18next-Init als Side-Effect) noch vor `App`.
- `main.tsx:8` — `applyTheme(getStoredTheme())` setzt das Theme aus localStorage **vor** dem ersten Render (kein Flash).
- `App.tsx:50` `App()` — `BrowserRouter` → `Routes`. Eine öffentliche Route (`/login`) + ein `Guard`-geschützter Layout-Tree, Catch-all `*` → Redirect auf `/`.
- `App.tsx:38` `Guard` — wenn kein `token` im `useAuthStore`, Redirect `/login`.
- `App.tsx:44` `AdminGuard` — wenn `role !== "admin"`, Redirect `/` (umschließt einzelne Routen, nicht das ganze Layout).
- `App.tsx:63` Index-Route: `getLanding() === "dashboard" ? <DashboardPage/> : <BuddyPage/>` — die Landing-Seite ist **per User-Präferenz** umschaltbar (localStorage `hh_landing`, Default `buddy`).
- Werkstatt-Chat-Routen: `App.tsx:68` `/werkstatt` und `App.tsx:69` `/werkstatt/:sid` → beide `<ChatPage/>`. `App.tsx:71` `/devchat` → permanenter Redirect auf `/werkstatt` (alter Name).
- Weitere Routen im Layout-Tree (vollständig): `/` (Buddy/Dashboard), `/buddy/settings`, `/dashboard`, `/health/*`, `/analytics/session/:sid`, `/werkstatt`, `/werkstatt/:sid`, `/scratchpad`, `/devchat`(redirect), `/agents`, `/projects`, `/communication`, `/vms`, `/containers`, `/containers/:id`, `/butler`, `/federation`, `/streaming`, `/datamining`, `/memory`, `/llm`, `/llm/catalog`, `/mcp`, `/skills`, `/credentials`, `/system`, `/users`(admin), `/plugins`(admin), `/extensions`(admin), `/profile`, `/help`, `/zahnfee`(admin), `*` → `<NotFoundPage/>`.

### Layout / Topbar (App-Shell-Chrome)

- `shared/Layout.tsx:14` `Layout()` — das gemeinsame Chrome um alle geschützten Seiten (`<Outlet/>`).
- Topbar-Elemente: Logo+„HydraHive"-Wortmarke (Link `/`), Breadcrumb („/ • aktueller Seitentitel" mit Domain-Farbpunkt), Quick-Link-Nav (nur ≥`lg`), Bento-Button (Grip-Icon), `AvatarMenu`.
- 3 fixierte Atmosphäre-Glows als Topbar-Hintergrund (violett oben-mitte, teal unten-links, amber unten-rechts) — `Layout.tsx:37-41`.
- `shared/BentoMenu.tsx:14` `BentoMenu` — App-Grid-Popover (alle Nav-Items nach Gruppen, 4-spaltiges Kachelraster, je Domain-Farbe), schließt bei Klick-außerhalb/Escape.
- `shared/AvatarMenu.tsx:8` `AvatarMenu` — Avatar-Initiale + grüner Online-Dot, Dropdown mit Username/Role, Link Profil, `LanguageSwitcher`, Logout.
- `shared/AppFooter.tsx:13` `AppFooter` — Statusleiste: Settings-Link, „online"-Dot, Version+Commit (monospace), Update-Indikator (↑-Button bei `update_behind>0`, RefreshCw bei force; nur Admin klickbar).
- `shared/nav-config.ts` — **SSOT der Navigation**: `NAV_GROUPS` (5 Gruppen: overview/working/automation/infrastructure/settings), `NAV_ITEMS` (24 Einträge, je `path`/`icon`/`labelKey`/`group`/optional `roles`), `QUICK_LINK_PATHS` (`/dashboard`,`/werkstatt`,`/agents`,`/projects`), `visibleItems(role)` (Rollen-Filter).
- `shared/CollapsibleSidebar.tsx:10` `CollapsibleSidebar` — generische rechte Einklapp-Sidebar (fixierter Toggle am Viewport-Rand), genutzt von Memory/Projects/Mcp/Agents — **nicht** vom Chat (Chat hat eigenes 3-Panel-Layout).

### Update- & Restart-Flow

- `shared/useLayoutUpdate.ts:5` `useLayoutUpdate()` — pollt `/health` alle 5 min (`version`/`commit`/`update_behind`), führt Update aus (`/system/check-update` Pre-Check → `/system/update` POST → `/health`-Poll auf Commit-Change, max 10 min).
- `shared/UpdateModal.tsx:17` `UpdateModal` — States `confirm/starting/running/done/failed`, Live-Log-Poll (`/system/update/log?tail=300`, 1.5 s während running).
- `shared/useRestart.ts:5` `useRestart()` — `/system/restart` POST + Health-Poll (down→up oder 3 healthy Polls nach 8 s), max 60 s.
- `shared/RestartModal.tsx:13` `RestartModal` — analoge State-Maschine, genutzt von SystemPage/PluginsPage (nicht im Chat).

### Theme & Domain-Farben (Redesign-System)

- `shared/theme.ts` — 5 Themes (`violet`(Standard)/`cool`/`warm`/`forest`/`mono`), `getStoredTheme()`/`applyTheme(id)` setzen `data-theme`-Attribut auf `<html>` (violet = Attribut entfernt = Default-Root-Vars), localStorage-Key `hh-theme`.
- `shared/colors.ts` — Domain-Farb-Mapping (`DOMAIN_COLORS` Pfad→Farbname), `colorFor(path)` (mit Longest-Prefix-Fallback), `DOMAIN_RGB` (Farbe→RGB-Tripel für `--c`), `rgbFor(path)` (Pfad→RGB für `.box`-Glow), `DOMAIN_TW` (Tailwind-Klassen-Map pro Farbe, weil Tailwind dynamische Klassen nicht tree-shaken kann).
- `index.css` — globaler Redesign-Layer: Root-CSS-Vars, 5 `[data-theme=…]`-Blöcke, `.light`-Variante, `.box`/`.tile`/`.sp`/`.bubble-user`/`.bubble-ai`/`.toolrow`/`.hh-app`/`img.hydra-emote`, themed Scrollbar.

### i18n

- `i18n/index.ts` — i18next-Init mit 33 Namespaces, `de`+`en`, `fallbackLng: "de"`, LanguageDetector (localStorage-Key `hh2.lang` → navigator), `defaultNS: "common"`, `escapeValue:false`.
- `i18n/LanguageSwitcher.tsx:5` `LanguageSwitcher` — DE/EN-Umschalter (Flaggen), `compact`-Variante für Avatar-Dropdown.
- `i18n/HelpButton.tsx:7` `HelpButton({topic})` — „?"-Button öffnet `HelpDrawer`.
- `i18n/HelpDrawer.tsx:13` `HelpDrawer` — rechtes Slide-Over, lädt Markdown-Hilfe lazy via `loadHelp`, rendert mit dem Chat-`Markdown`.
- `i18n/help/loader.ts:8` `loadHelp(topic,lang)` — Vite-Glob-Import `./*/*.md`, Fallback-Kette `<lang>` → `de` → `en` → Platzhalter. `HelpTopic` = `dashboard|chat|agents|projects|llm|mcp|system`.

### Chat — Seiten-Container & State

- `features/chat/ChatPage.tsx:40` `ChatPage` — Haupt-Container: lädt Sessions/Agents/Projekte, hält `activeId`, verdrahtet `useChat`, `useChatCompact`, Runtime, 3-Panel-Layout, Slash-Commands, Ctrl/Cmd+F-Suche, Pixel-Monitor-Toggle, Datei-Overlay.
- `features/chat/useChat.ts:33` `useChat(sessionId)` — zentrale Chat-State-Maschine (`messages/busy/compacting/iteration/error/errorKind/pendingConfirm/lastTurnTokens`) + `send`/`cancel`/`reload`/`confirmTool`.
- `features/chat/api.ts` — `chatApi` (REST: listSessions/createSession/deleteSession/updateSession/listMessages/logCmd/listAgents/listProjects/compact/tokens/toolConfirm) + `sendMessage()` (SSE-Streaming-Generator).
- `features/chat/types.ts` — Typen `Session`, `Message`, `ContentBlock` (text/thinking/image/tool_use/tool_result), `ImageSource`, `ToolMedia`, `AgentBrief`, `RunnerEvent` (das SSE-Wire-Format).
- `features/chat/_chatStream.ts:22` `applyStreamEvent()` + `updateLive()` — mappt jedes SSE-`RunnerEvent` auf `ChatState`-Mutationen (Live-Bubble-Aufbau).
- `features/chat/_assistantRuntime.ts:74` `useHydraRuntime()` + `convertMessage()` — Adapter auf `@assistant-ui/react` `useExternalStoreRuntime` (onNew/onEdit/onReload/onCancel).

### Chat — Thread, Bubbles, Header

- `features/chat/_ChatBubbleThread.tsx:188` `ChatBubbleThread` — **aktiver** Thread-Renderer (Card-Look): `ChatUserMessage`/`ChatAssistantMessage`/`ChatSystemMessage`.
- `features/chat/_ChatHeader.tsx:24` `ChatHeader` — Session-Titel (System-Prompt-Tooltip), ID-Kurz, Modell, Last-Turn-Tokens (↑↓⚡💾), `TokenMeter`, `HelpButton`, Neuer-Chat-Button, Compact-Button, Orphaned-Banner, `NewChatHint`.
- `features/chat/BubbleMeta.tsx` — `BubbleHeader` (Heute/Gestern/Datum + Uhrzeit, lokalisiert) und `AssistantFooter` (Tokens/Cache/Kosten/Modell/Iterationen/StopReason).
- `features/chat/_Thread.tsx:174` `HydraThread` — **toter/Legacy** alternativer Thread-Renderer (Gradient-Bubble-Look). Nirgends importiert (siehe Offene Enden).

### Chat — Eingabe & Commands

- `features/chat/MessageInput.tsx:23` `MessageInput` — Textarea (Auto-Grow max 200 px), Enter=Senden / Shift+Enter=Newline, Datei-Upload (Paperclip + Drag&Drop), Mic-Button (Voice-Input), `EmotePicker`, Stop/Senden-Button, `quickActions`-Slot, Datei-Chips.
- `features/chat/commands.ts` — Slash-Command-Engine `runChatCommand()` + `isCommand()`. Befehle: `/help`, `/clear`(=`/reset`), `/model`(=`/models`), `/compact`, `/tokens`, `/title`(=`/rename`), `/system`(=`/sys`), `/tools`, `/agent`, `/skills`(=`/skillkatalog`), `/export`, und **dynamisch `/<skillname>`** (führt Skill-Body an den Agent).
- Quick-Action-Pills in `ChatPage.tsx:272-285`: help, clear, compact, tokens, title (insert), system, tools, agent, export, `SkillCatalogPill`, pixel (Toggle).
- `features/chat/_SkillCatalogPill.tsx:11` `SkillCatalogPill` — Popover mit Skill-Chips; Klick fügt `Nutze den Skill "name": ` in die Eingabe ein.
- `features/chat/_MessageFileChip.tsx:5` `MessageFileChip` — Datei-Vorschau-Chip (Bild-Thumbnail oder FileText) mit Entfernen-X.
- `features/chat/NewSessionDialog.tsx:14` `NewSessionDialog` — Modal: Modus direct/project, Agent-/Projekt-Auswahl, optionaler Titel.
- `features/chat/NewChatHint.tsx:12` `NewChatHint` — gelber Hinweis „Kontext groß" ab 20 k Input-Tokens, schlägt neuen Chat vor (geschätzte Ersparnis ggü. 10 k Baseline).

### Chat — Modell- & Effort-Steuerung

- `features/chat/SessionModelControls.tsx:19` `SessionModelControls` — Modell-Picker + Reasoning-Effort-Pill am Fuß der SessionList; kapselt Agent-Default-vs-Session-Override-Logik.
- `features/chat/ModelPicker.tsx:23` `ModelPicker` — native `<select>` mit Live-Modellliste (`llmInfoApi.getModels`), optionale Reset-Option, fullWidth-Modus.
- `features/chat/ReasoningEffortPill.tsx:19` `ReasoningEffortPill` — Dropdown (off/low/medium/high; bei `extended` zusätzlich xhigh/max). Typ `EffortLevel`.
- `features/llm/effort.ts` — `useEffortPrefixes()`/`modelSupportsExtendedEffort()` holen die xhigh/max-fähigen Modell-Präfixe live vom Backend (`/llm/effort-models`, SSOT-Cache).

### Chat — Token- & Compaction-UI

- `features/chat/TokenMeter.tsx:18` `TokenMeter` — Balken used/compact_threshold, Farbton ab 50/80 %, Warn-Pill ab 90 %.
- `features/chat/useChatCompact.ts:5` `useChatCompact()` — manuelle Compaction (`/compact`), übersetzte Skip-/Erfolgs-Notiz, Auto-Clear nach 5 s.
- `features/chat/CompactionBlock.tsx:6` `CompactionBlock` — aufklappbare Compaction-Zusammenfassung (Tokens gespart, gelesene/geänderte Dateien, Summary-Text).
- `features/chat/ThinkingBlock.tsx:8` `ThinkingBlock` — aufklappbarer „Reasoning"-Block für `thinking`-Content.

### Chat — Tool-Cards & Banner

- `features/chat/ToolCards.tsx` — `ToolUseCard` (aufklappbarer Tool-Aufruf mit Args+Dauer), `ToolResultCard` (Auto-Collapse ab 300 Zeichen/8 Zeilen, ruft spezialisierte Card oder Pre-Block), `ImageBlock` (Inline-Bild aus `image`-Block). Plugin-Prefix-`strip()` für Tool-Namen.
- `features/chat/tool_cards/ShellExecCard.tsx:26` `ShellExecCard` — strukturiert für `shell_exec` (exit_code/stdout/stderr/timed_out, aufklappbare Sektionen).
- `features/chat/tool_cards/WebSearchCard.tsx:29` `WebSearchCard` — Trefferliste (title/url/snippet) für `web_search`.
- `features/chat/tool_cards/GitDiffCard.tsx:36` `GitDiffCard` — color-coded Diff (+/-/@@) für `git_diff` (plugin__git-stats__git_diff).
- `features/chat/ToolConfirmBanner.tsx:17` `ToolConfirmBanner` — Approve/Deny-Banner bei `tool_confirm_required` (zeigt Tool-Name + gekürzte Args).

### Chat — Medien, Emotes, Markdown, Suche, Voice, Pixel-Monitor

- `features/chat/Markdown.tsx:26` `Markdown` — `react-markdown` + `remark-gfm` + `remarkHydraEmotes`; Code-Highlighting (Prism vscDarkPlus) mit Copy-Button, Tabellen-Styling, Hydra-Emote-Img-Override.
- `features/chat/MediaPreview.tsx` — `extractMedia()`/`mediaFromBlocks()`/`hasMedia()` + `MediaPreview`/`PdfViewer`. Erkennt Bild/Audio/Video/PDF/EPUB (HTTP-URLs + absolute `/tmp`+`/var/lib/hydrahive2`-Pfade → `/api/files?path=…&token=…`).
- `features/chat/ImageLightbox.tsx:17` `ImageLightbox` — Thumbnail → Vollbild-Overlay (Escape/Klick zu, Download-Button).
- `features/chat/EpubViewer.tsx:13` `EpubViewer` — inline epub.js-Reader (paginated, prev/next).
- `features/chat/hydraEmotes.ts` — `:hydra-NAME:`-System: `HYDRA_EMOTES`-Map (aus `_emoteNames.generated.ts`), `ALIASES` (heart→love etc.), `EMOTE_RE`, `tokenizeEmotes()`.
- `features/chat/_emoteNames.generated.ts` — **auto-generierte** Liste von 152 Emote-Namen (Quelle: PNGs, via `scripts/gen-emotes.mjs` als `prebuild`).
- `features/chat/EmoteText.tsx:4` `EmoteText` — rendert Plain-Text-Bubbles mit inline Emotes.
- `features/chat/EmotePicker.tsx:9` `EmotePicker` — 7-spaltiges Emote-Raster-Popover, Klick fügt `:hydra-name:` ein.
- `features/chat/remarkHydraEmotes.ts:32` `remarkHydraEmotes` — remark-Plugin, ersetzt `:hydra-NAME:` in Text-Knoten durch Bild-Knoten (Code-Blöcke bleiben unangetastet).
- `features/chat/ChatSearchContext.tsx` — `ChatSearchProvider`/`useChatSearch()`: In-Thread-Suche (Query→Match-Liste, next/prev, activeMessageId).
- `features/chat/ChatSearchBar.tsx:6` `ChatSearchBar` — Suchleiste (Enter/F3=next, Shift=prev, Escape=close, Treffer-Zähler).
- `features/chat/useVoiceInput.ts:26` `useVoiceInput()` — Mikrofon-Aufnahme (MediaRecorder, MIME-Auswahl iOS/Android), POST `/api/stt`, gibt Transkript zurück.
- `features/chat/useVoiceOutput.ts:155` `useVoiceOutput()` — TTS-Singleton (nur **eine** aktive Stimme app-weit), 4 Provider (`browser`/`local`/`minimax`/`openrouter`), POST `/api/tts`, localStorage `hh_tts_provider`/`hh_tts_voice`.
- `features/chat/AgentPixelMonitor.tsx:88` `AgentPixelMonitor` — Canvas-„Minecraft"-Pixel-Animation der aktiven Agenten (Tool-Bubbles, Connection-Lines, active/waiting/done-States).
- `features/chat/_mcCharacters.ts` — 12 Pixel-Charakter-Templates (Steve/Alex/Zombie/…), `getCharForAgent(name)` (deterministischer Hash→Template).

### Chat — Session-Liste & 3-Panel-Layout

- `features/chat/SessionList.tsx:27` `SessionList` — linkes Panel: Tabs direct/projects/buddy, Paused-First-Sort, Orphan-Markierung, Lösch-Confirm, eingebettete `SessionModelControls`.
- `features/chat/layout/ThreePanelLayout.tsx:24` `ThreePanelLayout` — Sessions | Chat | Workspace; Panel-Zustand in localStorage (`hh2.chat.panels`), Default auf schmalen Screens beide zu.
- `features/chat/layout/CollapsiblePanel.tsx:11` `CollapsiblePanel` — generisches links/rechts einklappbares Panel mit mittigem Toggle-Handle.

### Workspace-Panel (Files / Git / Monaco / Media)

- `features/chat/workspace/WorkspacePanel.tsx:15` `WorkspacePanel` — rechtes Panel, Tabs files/git; `.box`-Optik in Werkstatt-Domain-Farbe.
- `features/chat/workspace/FileTree.tsx:7` `FileTree` — rekursiver, lazy-ladender Verzeichnisbaum (`/workspace/tree`), Klick auf Datei → `onOpen`.
- `features/chat/workspace/fileType.ts` — `classifyFile(path)` → `text|image|video|audio|download` (Endungs-Sets, Binär→Download).
- `features/chat/workspace/FileOverlay.tsx:16` `FileOverlay` — Vollbild-Datei-Overlay (Escape zu); `text`→`FileEditor`, sonst `MediaViewer`.
- `features/chat/workspace/FileEditor.tsx:25` `FileEditor` — lazy-geladener Monaco-Editor mit Speichern, Dirty-Marker, Sprach-Erkennung aus Endung.
- `features/chat/workspace/monacoSetup.ts` — lokales Monaco-Bundling (kein CDN), Vite-Worker-Verdrahtung (json/css/html/ts + editor.worker).
- `features/chat/workspace/MediaViewer.tsx:9` `MediaViewer` — Bild/Video/Audio/Download-Viewer via `rawObjectUrl` (Blob + Object-URL).
- `features/chat/workspace/GitPanel.tsx:5` `GitPanel` — Repo-Picker, Status-Auto-Refresh (4 s), Stage-Checkbox, Diff-Vorschau, Commit-Box.
- `features/chat/workspace/useWorkspace.ts:4` `useWorkspace(agentId)` — `open`/`save`-Hook für die `FileContent`.
- `features/chat/workspace/api.ts` — `workspaceApi` (tree/file/save/rawObjectUrl) + `gitApi` (repos/status/diff/stage/commit).

### Backend-Endpoints (vom Chat/Workspace konsumiert)

- `/sessions` GET/POST, `/sessions/{id}` GET/PATCH/DELETE, `/sessions/{id}/tool-confirm/{call_id}` POST — `core/src/hydrahive/api/routes/sessions.py:29,35,53,65,85,97`.
- `/sessions/{id}/messages` GET — `sessions_messages.py:31`; `/sessions/{id}/messages` POST (SSE) — `sessions_messages.py:133`; `/sessions/{id}/messages/{mid}/resend` POST — `sessions_messages.py:106`; `/sessions/{id}/tokens` GET — `sessions_messages.py:57`; `/sessions/{id}/compact` POST — `sessions_messages.py:79`; `/sessions/{id}/log-cmd` POST — `sessions_messages.py:154`.
- `/workspace/tree|file(get/put)|raw|git/repos|git/status|git/diff|git/stage|git/commit` — `workspace.py:27,46,71,88,124,133,142,164,187` (Router-Prefix `/api/workspace`).
- `/files` GET — `files.py:67` (Media via `?path=…&token=…`); `/stt` POST — `stt.py:19`; `/tts` POST + `/tts/voices` GET — `tts.py:59,37`.

---

## WIE

### Boot-Reihenfolge

1. `main.tsx` importiert `index.css` (Tailwind + Redesign) und `./i18n` (initialisiert i18next synchron beim Import).
2. `applyTheme(getStoredTheme())` setzt das `data-theme`-Attribut **vor** dem React-Mount.
3. `createRoot().render(<App/>)` → `BrowserRouter` → `Routes`.
4. `Guard` liest `token` aus dem Zustand-Store; ohne Token sofort `/login`. Mit Token rendert `Layout` mit `<Outlet/>`.

### Layout-Render-Pfad

- `Layout` liest `role` (Store), `nav`-Translations, `pathname`. `visibleItems(role)` filtert die Nav nach Rolle. `currentPage` per Pfad-Match für Breadcrumb. `QUICK_LINK_PATHS` werden auf sichtbare Items gemappt für die Topbar-Quick-Nav.
- `useLayoutUpdate()` pollt `/health` (5 min) → Footer-Version/Update-Indikator. Klick öffnet `UpdateModal` (nur `updateState !== "idle"` rendert es).

### Chat — Daten- & Sende-Fluss (Kernpfad)

1. **Mount/Session-Wahl**: `ChatPage.loadAll()` (`Promise.all` Sessions/Agents/Projekte). Deep-Link `:sid` oder `?session=` wird einmalig (`deepLinkApplied`-Ref) angewendet; sonst erste Session. Bei Fehler `loadError`-Toast (nicht still schlucken, #211). `ChatPage.tsx:62-86`.
2. **Reload bei `activeId`-Wechsel**: `useEffect` setzt `localMsgs=[]` + `chat.reload()` → `chatApi.listMessages` füllt `state.messages`. `ChatPage.tsx:86`.
3. **Senden** (`handleSend`, `ChatPage.tsx:129`): wenn `isCommand(text)` → `runChatCommand` (deterministisch, evtl. `sendToAgent`/`newSessionId`/`agentChanged`/`sessionChanged`); sonst direkt `chat.send(text, files)`.
4. **`useChat.send`** (`useChat.ts:51`): baut optimistisch `userMsg` (+ Image-Blocks aus Files als Object-URL) und leere `liveAssistant`-Bubble (`id` mit `live-`-Prefix); setzt `busy=true`. Bei `resendMessageId` wird die History bis dahin abgeschnitten (Branch/Edit).
5. **Stream**: `sendMessage()` (`api.ts:43`) POSTet `FormData` an `/api/sessions/{id}/messages` (oder `…/resend`), liest den SSE-Body manuell (`getReader`+`TextDecoder`, Frame-Split an `\n\n`, `data: `-Zeilen JSON-parsen). `resendMessageId` mit `local-`-Prefix → kein Resend (existiert nur im Frontend).
6. **Event-Apply** (`applyStreamEvent`, `_chatStream.ts:22`): `iteration_start`/`message_start`/`text_delta`(+=)/`text`/`tool_use_start`/`tool_confirm_required`(→`pendingConfirm`)/`tool_use_result`(→`tool_result`-Block, löscht pendingConfirm)/`compaction_start`/`error`(→`errorKind`)/`done`(→`lastTurnTokens`). `updateLive()` ersetzt die letzte `live-`-Bubble mit den akkumulierten Blocks.
7. **Abschluss**: bei `done` → `await reload()` (holt die persistierten Messages frisch). Abbruch via `AbortController` (`cancel()`); AbortError wird nicht als Fehler angezeigt, danach `reload()`.
8. **Rendering**: `allMessages = [...chat.messages, ...localMsgs]` → `useHydraRuntime` → `AssistantRuntimeProvider` (`key={activeId}` erzwingt frischen Runtime pro Session). `ChatBubbleThread` rendert via `@assistant-ui/react`-Primitives.

### Slash-Command-Zustandsmaschine (`commands.ts:137`)

- Trennt `cmd` (vor erstem Space, lowercased) und `arg`. `switch`: feste Befehle rufen Backend (`agentsApi`/`chatApi`/`skillsApi`) und liefern `ChatCommandResult`. Default: behandelt `cmd` als Skill-Name → `sendToAgent` mit Skill-Body.
- In `handleSend`: `sendToAgent` → echter `chat.send`. Sonst werden `appendLocal("user")` + `appendLocal("assistant")` als **lokale** `local-cmd-…`-Bubbles gezeigt, danach `chatApi.logCmd` persistiert die Q&A in der Session und `chat.reload()` ersetzt sie. `newSessionId` → Session-Wechsel; `agentChanged`/`sessionChanged` aktualisieren lokale Listen optimistisch.

### Runtime-Adapter (`_assistantRuntime.ts`)

- `convertMessage` mappt HH2-`Message` → `ThreadMessageLike`: Rollen-Mapping (`compaction`/`system`→`system`, `tool`→`assistant`), Tool-Use+Tool-Result werden zu einem `tool-call`-Part zusammengeführt (Result via `tool_use_id`-Map). Originale `Message`-Objekte bleiben via `metadata.custom` erreichbar.
- `getExternalStoreMessages<Message>(msg)` in den Bubble-Komponenten holt das Original zurück (für Raw-JSON, Token-Footer, Emote-Text, Media).
- `onReload` (Retry) findet den passenden User-Parent und ruft `send(text,[],parent.id)`; `onEdit` nutzt `parentId`; `onNew` sendet neue Nachricht.

### Workspace-Fluss

- `WorkspacePanel` rendert nur bei `agentId`. Files-Tab: `FileTree` lädt `/workspace/tree?agent_id&path` lazy je Ordner. Klick → `classifyFile(path)` → `ChatPage.setWsFile` → `FileOverlay`.
- `FileOverlay`: `text` → `useWorkspace.open` lädt `/workspace/file` → `FileEditor` (Monaco lazy, `monacoSetup` zuerst). Speichern → `/workspace/file` PUT → lokaler `openFile.content`-Update.
- Nicht-Text → `MediaViewer` lädt `/workspace/raw` als Blob → Object-URL (mit Cleanup via `revokeObjectURL`).
- Git-Tab: `GitPanel` lädt Repos einmalig, pollt Status alle 4 s, Stage/Diff/Commit über `gitApi`.

### Media-Resolution (`MediaPreview.tsx`)

- Bevorzugt strukturierte `tool_result.media[]` (`mediaFromBlocks`); Fallback Regex-Extraktion aus Freitext (`extractMedia`). Absolute Pfade unter `/tmp` bzw. `/var/lib/hydrahive2` → `/api/files?path=…&token=…` (Token als Query-Param, weil `<img>` keinen Auth-Header sendet).

### TTS-Singleton-Logik (`useVoiceOutput.ts`)

- Modul-globale Refs (`activeAudio`/`activeAudioUrl`/`speakRequestId`) + Listener-Sets. `speakGlobal` ruft `stopAll()` (invalidiert laufende Requests via `speakRequestId`), holt Audio-Blob vom Backend (oder Browser-`SpeechSynthesis`), spielt ab. Kein Cross-Provider-Fallback (entweder/oder). `useVoiceOutput`-Hook abonniert nur die Listener.

### i18n-Fehlermeldungen (`api-client.ts`)

- `request()` setzt Auth-Header, behandelt 401 (Logout + Throw), 204 (undefined), Fehler → `buildErrorMessage` übersetzt `{detail:{code,params}}` über den `errors`-Namespace (`errors:CODE`).

---

## WO

### Shell / Routing / Layout

- `App.tsx:38` `Guard`, `App.tsx:44` `AdminGuard`, `App.tsx:50` `App`, `App.tsx:63` Landing-Switch, `App.tsx:68-71` Werkstatt-/devchat-Routen.
- `shared/Layout.tsx:14` `Layout`, `:19-23` `useLayoutUpdate`-Destrukturierung, `:30-32` `currentPage`, `:37-41` Glows, `:44-95` Topbar, `:100-102` `<Outlet/>`, `:104-116` Footer+UpdateModal.
- `shared/nav-config.ts:19` `NAV_GROUPS`, `:27` `NAV_ITEMS`, `:60` `QUICK_LINK_PATHS`, `:62` `visibleItems`.
- `shared/BentoMenu.tsx:14`, `shared/AvatarMenu.tsx:8`, `shared/AppFooter.tsx:13`, `shared/CollapsibleSidebar.tsx:10`.
- `shared/useLayoutUpdate.ts:5` `useLayoutUpdate`, `:24` `confirmUpdate`; `shared/UpdateModal.tsx:6` `UpdateState`, `:17` `UpdateModal`.
- `shared/useRestart.ts:5` `useRestart`, `shared/RestartModal.tsx:4` `RestartState`, `:13` `RestartModal`.
- `shared/api-client.ts:24` `request`, `:50` `api`-Objekt, `:13` `buildErrorMessage`.
- `shared/HydraMascot.tsx:29` `HydraMascot` (8 States), `shared/EmptyState.tsx:10` `EmptyState`, `shared/NotFoundPage.tsx:4` `NotFoundPage`, `shared/cn.ts:4` `cn`.

### Theme & Farben

- `index.css:6-44` Root-Vars, `:46-88` Theme-Blöcke, `:90-108` `.light`, `:111-129` Scrollbar, `:137-147` `.hh-app`, `:150-191` `.box`, `:194-206` `.tile`, `:209-216` `.sp`, `:219-242` Bubbles/Toolrow, `:246-253` `img.hydra-emote`.
- `shared/theme.ts:11` `THEMES`, `:26` `getStoredTheme`, `:32` `applyTheme`.
- `shared/colors.ts:15` `DOMAIN_COLORS`, `:37` `colorFor`, `:48` `DOMAIN_RGB`, `:55` `rgbFor`, `:62` `DOMAIN_TW`.

### i18n

- `i18n/index.ts:71` `resources`, `:96` `SUPPORTED_LANGUAGES`, `:101-116` Init, `:108` ns-Array, `:114` `lookupLocalStorage: "hh2.lang"`.
- `i18n/LanguageSwitcher.tsx:5`, `i18n/HelpButton.tsx:7`, `i18n/HelpDrawer.tsx:13`, `i18n/help/loader.ts:4` `HelpTopic`, `:8` `loadHelp`.

### Chat — Core

- `features/chat/ChatPage.tsx:40` `ChatPage`, `:62` `loadAll`, `:88` `handleNew`, `:93` `handleDelete`, `:120` `appendLocal`, `:129` `handleSend`, `:166` `pixelData`, `:212` `center`, `:298` Provider/Layout.
- `features/chat/useChat.ts:12` `ChatState`, `:33` `useChat`, `:37` `cancel`, `:41` `reload`, `:51` `send`, `:94` `confirmTool`.
- `features/chat/api.ts:12` `chatApi`, `:43` `sendMessage`, `:95` `parseSseFrame`.
- `features/chat/types.ts:1` `Session`, `:19` `ContentBlock`, `:34` `Message`, `:43` `AgentBrief`, `:52` `RunnerEvent`.
- `features/chat/_chatStream.ts:8` `updateLive`, `:22` `applyStreamEvent`.
- `features/chat/_assistantRuntime.ts:22` `convertMessage`, `:74` `useHydraRuntime`.

### Chat — UI

- `features/chat/_ChatBubbleThread.tsx:36` `ChatUserMessage`, `:92` `ChatAssistantMessage`, `:180` `ChatSystemMessage`, `:188` `ChatBubbleThread`, `:25` `hl`.
- `features/chat/_ChatHeader.tsx:24` `ChatHeader`.
- `features/chat/BubbleMeta.tsx:28` `BubbleHeader`, `:49` `AssistantFooter`, `:4` `formatBubbleTime`.
- `features/chat/MessageInput.tsx:23` `MessageInput`, `:8-10` Limits (`MAX_FILES=5`, `MAX_IMAGE_BYTES=5MB`, `MAX_TEXT_BYTES=100KB`).
- `features/chat/commands.ts:35` `isCommand`, `:137` `runChatCommand`, `:20` `HELP_TEXT`.
- `features/chat/SessionList.tsx:27` `SessionList`, `:117` `TabButton`, `:130` `SessionRow`.
- `features/chat/SessionModelControls.tsx:19`, `features/chat/ModelPicker.tsx:23`, `features/chat/ReasoningEffortPill.tsx:19` (`:5` `EffortLevel`).
- `features/chat/TokenMeter.tsx:18`, `features/chat/useChatCompact.ts:5`, `features/chat/CompactionBlock.tsx:6`, `features/chat/ThinkingBlock.tsx:8`.
- `features/chat/ToolCards.tsx:11` `strip`, `:17` `specializedCard`, `:25` `formatDuration`, `:31` `ToolUseCard`, `:64` `ToolResultCard`, `:120` `ImageBlock`; `:61-62` Collapse-Schwellen.
- `features/chat/tool_cards/ShellExecCard.tsx:26`, `WebSearchCard.tsx:29`, `GitDiffCard.tsx:36`.
- `features/chat/ToolConfirmBanner.tsx:17`, `features/chat/NewSessionDialog.tsx:14`, `features/chat/NewChatHint.tsx:12` (`:4-5` Schwellen 20k/10k).
- `features/chat/_SkillCatalogPill.tsx:11`, `features/chat/_MessageFileChip.tsx:5`.

### Chat — Media/Emotes/Voice/Search/Pixel

- `features/chat/Markdown.tsx:9` `CopyCodeButton`, `:26` `Markdown`.
- `features/chat/MediaPreview.tsx:56` `extractMedia`, `:81` `mediaFromBlocks`, `:98` `PdfViewer`, `:123` `MediaPreview`, `:16-30` Regexe.
- `features/chat/ImageLightbox.tsx:17`, `features/chat/EpubViewer.tsx:13`.
- `features/chat/hydraEmotes.ts:11` `HYDRA_EMOTES`, `:16` `ALIASES`, `:23` `EMOTE_RE`, `:30` `tokenizeEmotes`; `features/chat/_emoteNames.generated.ts:3` `EMOTE_NAMES`.
- `features/chat/EmoteText.tsx:4`, `features/chat/EmotePicker.tsx:9`, `features/chat/remarkHydraEmotes.ts:32`.
- `features/chat/ChatSearchContext.tsx:16` `useChatSearch`, `:35` `ChatSearchProvider`, `:23` `msgText`; `features/chat/ChatSearchBar.tsx:6`.
- `features/chat/useVoiceInput.ts:26` `useVoiceInput`, `:107` `transcribe`, `:8` `PREFERRED_MIMES`.
- `features/chat/useVoiceOutput.ts:155` `useVoiceOutput`, `:67` `speakGlobal`, `:48` `stopAll`, `:4` `TTSProvider`, `:7-8` Storage-Keys, `:9` `DEFAULT_VOICE`.
- `features/chat/AgentPixelMonitor.tsx:88`, `:29` `drawChar`, `:47` `drawBubble`, `:9` `TOOL_BUBBLE`; `features/chat/_mcCharacters.ts:7` `CHARACTERS`, `:34` `getCharForAgent`.

### Chat — Layout & Workspace

- `features/chat/layout/ThreePanelLayout.tsx:24` `ThreePanelLayout`, `:5` `STORAGE_KEY="hh2.chat.panels"`, `:7` `loadState`.
- `features/chat/layout/CollapsiblePanel.tsx:11`.
- `features/chat/workspace/WorkspacePanel.tsx:15`, `useWorkspace.ts:4`, `FileTree.tsx:7`, `fileType.ts:15` `classifyFile`, `FileOverlay.tsx:16`, `FileEditor.tsx:25` (`:12` `langFromPath`), `monacoSetup.ts:11` `MonacoEnvironment`, `MediaViewer.tsx:9`, `GitPanel.tsx:5` (`:36` `doCommit`), `workspace/api.ts:7` `workspaceApi`, `:33` `gitApi`.

### Backend-Routen

- `core/src/hydrahive/api/routes/sessions.py:29,35,53,65,85,97`.
- `core/src/hydrahive/api/routes/sessions_messages.py:31,57,79,106,133,154`.
- `core/src/hydrahive/api/routes/workspace.py:27,46,71,88,124,133,142,164,187`.
- `core/src/hydrahive/api/routes/files.py:67`, `stt.py:19`, `tts.py:37,59`.

---

## WARUM

### Architektur-/Render-Invarianten

- **`live-`-Prefix-Konvention**: `useChat.send` legt eine Platzhalter-Bubble mit `id` `live-…` an; `updateLive` ersetzt **nur** die letzte Nachricht **wenn** ihre ID mit `live-` beginnt (`_chatStream.ts:15`). Wer diese Prefix-Konvention ändert, bricht das gesamte Streaming-Rendering.
- **`local-` / `local-cmd-`-Prefixe**: Frontend-only IDs, die nie in der DB existieren. `sendMessage` verweigert Resend für `local-`-IDs (`api.ts:55`). Slash-Command-Bubbles sind `local-cmd-…` und werden nach `logCmd`+`reload` durch die persistierte Version ersetzt. Bricht man die Prefix-Logik, werden Commands doppelt oder als echte Agent-Nachrichten gesendet.
- **`AssistantRuntimeProvider key={activeId}`** (`ChatPage.tsx:299`): erzwingt einen frischen Runtime pro Session — sonst leakt der Branch-/Edit-State der vorigen Session in die neue.
- **`allMessages = [...chat.messages, ...localMsgs]`**: lokale Command-Bubbles werden **angehängt**, leben getrennt von der echten History. Bei Session-Wechsel werden `localMsgs` geleert (`ChatPage.tsx:86`), sonst würden Command-Antworten in fremden Sessions auftauchen.
- **`ToolResultCard` ruft `useState` vor jedem early-return** (`ToolCards.tsx:71-73`): Kommentar warnt explizit vor React-Fehler #310 (Hook-Count darf zwischen Renders nicht wechseln, je nachdem ob eine spezialisierte Card greift).
- **`deepLinkApplied`-Ref** (`ChatPage.tsx:45,71`): Deep-Link wird **genau einmal** angewendet, sonst springt jeder `loadAll`-Reload zurück auf die URL-Session und überschreibt die manuelle Auswahl.
- **`loadAll`-`useEffect` ohne Deps** (`ChatPage.tsx:84-85`): bewusst nur beim Mount; `loadAll` in den Deps würde Re-Run pro Render auslösen (eslint-disable mit Begründung).

### Redesign-/Box-System-Invarianten

- **`.box` braucht nur `--c` (Domain-RGB)**: Eine Box bekommt ihre komplette Optik (Farbwasch, leuchtender Rand, Halo, Hover-Lift) allein über `style={{ "--c": rgbFor(path) }}`. Deshalb `DOMAIN_RGB` als RGB-Tripel ohne `rgb()`-Wrapper (das CSS macht `rgb(var(--c) / …)`). `index.css:150`.
- **`DOMAIN_TW` ist hardcoded, weil Tailwind dynamische Klassen nicht tree-shaken kann** (`colors.ts:59-65`). Man darf Klassen wie `bg-${color}-500` nur dort vorberechnen — und in `ToolResultCard.tsx:96-98` wird genau dieses Muster (`border-${color}-500/15`) verwendet, was nur funktioniert, weil rose/emerald in der Tailwind-Safelist/Content stehen; sonst würde die Farbe stumm verschwinden.
- **Theme = `data-theme`-Attribut, `violet` = Attribut entfernt** (`theme.ts:34`): die Default-Akzent-Vars stehen im `:root`, nicht in einem `[data-theme=violet]`-Block — wer einen solchen Block hinzufügt, dupliziert die SSOT.
- **Cache-/Volatile-Hinweis indirekt relevant**: `BubbleHeader` rendert „Heute/Gestern" lokalisiert; das ist reine Anzeige, aber zeigt das Muster, Zeit erst client-seitig zu formatieren.

### Streaming/SSE-Invarianten

- **SSE wird manuell geparst**, nicht via `EventSource` — weil POST mit `FormData` (Datei-Upload) nötig ist und `EventSource` nur GET kann. Frame-Trennung an `\n\n`, `data:`-Zeilen werden konkateniert (`api.ts:80-92`). Mehrzeilige `data:`-Frames werden unterstützt.
- **`done` triggert `reload()`** statt die Live-Bubble zu behalten: die persistierte Nachricht hat die echten Metadaten (Token-Footer, Modell, Iteration) — die Live-Bubble nicht. Deshalb „flackert" die letzte Nachricht kurz beim Abschluss (Live → reloaded).
- **AbortError ist kein Fehler** (`useChat.ts:82`): Cancel via `AbortController` darf keine rote Fehlerzeile zeigen; danach `reload()` um den Teilstand zu verwerfen.
- **`errorKind === "max_iterations"`** (`ChatPage.tsx:245`): zeigt einen „Weitermachen"-Button, der eine Fortsetzungs-Nachricht sendet — die einzige Stelle, an der `errorKind` UI-Verhalten steuert. Paused-Sessions bekommen in `SessionList` ein Play-Icon (`SessionList.tsx:147`).

### Auth-/Media-Invarianten

- **Token als Query-Param bei Media** (`MediaPreview.tsx:32-37`, `workspace/api.ts:17`): `<img>/<audio>/<video>` können keinen `Authorization`-Header schicken → Backend akzeptiert `?token=`. Wer das Backend auf header-only umstellt, bricht alle Inline-Medien.
- **Object-URLs müssen revoked werden**: `MediaViewer`/`useVoiceOutput`/`workspaceApi.rawObjectUrl` haben explizite Cleanup-Pfade; der Caller von `rawObjectUrl` ist laut Kommentar verantwortlich.

### Voice-Invarianten

- **TTS ist ein Modul-Singleton** (`useVoiceOutput.ts:19-21`): mehrere Bubbles teilen sich `activeAudio` — sonst spielen mehrere Stimmen gleichzeitig. `speakRequestId` invalidiert in-flight `speak`-Promises (Race bei schnellem Re-Klick/Unmount).
- **Kein Cross-Provider-Fallback** (`useVoiceOutput.ts:122`): explizit „entweder/oder, nie beides" — sonst doppelte Ausgabe (server-TTS + Browser-TTS).
- **Voice-Input MIME-Auswahl** (`useVoiceInput.ts:8-24`): iOS Safari kann nur `audio/mp4`, Android bevorzugt webm; Reihenfolge ist bewusst. `start(250)` + `requestData`/`setTimeout`-Safety, weil iOS `onstop`/`ondataavailable` unzuverlässig feuert.

### i18n-Invarianten

- **Namespace-Array muss zu `resources` passen** (`i18n/index.ts:108`): jeder importierte Namespace muss in `ns:[…]` stehen, sonst lädt i18next ihn nicht (Memory-Note: „i18n-Namespaces waren nie registriert" war ein früherer Bug). 33 Namespaces de+en.
- **`errors`-Namespace ist der Fehler-Übersetzungskanal** (`api-client.ts:17`): das Backend liefert `{detail:{code,params}}`, der Client übersetzt `errors:CODE`. Bricht man diese Konvention, sieht der User nur rohe Codes.

### Workspace-Invarianten

- **Monaco lokal gebündelt, kein CDN** (`monacoSetup.ts:1`): self-hosted-Anforderung. Worker werden über Vite-`?worker`-Imports verdrahtet; `FileEditor` lädt `monacoSetup` **vor** `@monaco-editor/react` im selben Lazy-Chunk (`FileEditor.tsx:7-10`), sonst läuft Monaco gegen die Default-CDN-Config.
- **`classifyFile` entscheidet text vs. media vor dem Laden** (`fileType.ts`): bekannte Binär-Endungen gehen direkt auf Download, ohne den Versuch, sie als Text zu laden (verhindert kaputte Riesen-Strings).
- **GitPanel pollt 4 s, repo-default = erstes Repo** (`GitPanel.tsx:16-31`): `_root` wird als „/" angezeigt. Commit-Button ist nur aktiv, wenn mindestens eine Datei gestaged ist.

---

## Datenmodell

### Frontend-State-Typen (`features/chat/types.ts`, `useChat.ts`)

- `Session`: `id, agent_id, user_id, project_id|null, title|null, status, created_at, updated_at, metadata`. Relevante `metadata`-Keys: `model_override` (Session-Modell-Override), `reasoning_effort`.
- `Message`: `id, role(user|assistant|tool|system|compaction), content(string|ContentBlock[]|null), created_at, token_count|null, metadata`.
- `ContentBlock`-Union: `text` | `thinking{thinking,signature?}` | `image{source}` | `tool_use{id,name,input,duration_ms?}` | `tool_result{tool_use_id,content,is_error?,duration_ms?,media?,tool_name?}`.
- `ImageSource`: `{base64,media_type,data}` | `{url}`. `ToolMedia`: `{kind: image|audio|video|pdf|epub, path?, url?}`.
- `AgentBrief`: `id, name, type, llm_model, status, is_buddy?`.
- `RunnerEvent` (SSE-Wire): `compaction_start | iteration_start | message_start | text_delta | text | tool_use_start | tool_confirm_required | tool_use_result | done{…token-felder} | error{message,fatal}`.
- `ChatState`: `messages, busy, compacting, iteration, error, errorKind, pendingConfirm, lastTurnTokens{input,output,cache_creation,cache_read}`.
- `PendingConfirm`: `call_id, tool_name, arguments` (in `useChat.ts` und `ToolConfirmBanner.tsx` doppelt definiert — siehe Offene Enden).
- Assistant-`metadata` (von `AssistantFooter` gelesen): `input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, model, iteration, stop_reason`, plus `source` (`slash_command`).
- `compaction`-`metadata` (`CompactionBlock`): `tokensBefore, readFiles[], modifiedFiles[]`.

### Nav-/Domain-Konfiguration

- `NavItem`: `path, icon, labelKey, group, roles?`. `NavGroup`: `key, labelKey`.
- `DomainColor`-Union (14 Farben), `DOMAIN_COLORS` (Pfad→Farbe), `DOMAIN_RGB`, `DOMAIN_TW`.
- `ThemeId`: `violet|cool|warm|forest|mono`; `ThemeMeta{id,name,description,preview{from,to}}`.

### CSS-Custom-Properties (`index.css`)

- shadcn-Basis: `--background,--foreground,--card,--border,--input,--ring,--primary,--secondary,--muted,--accent,--destructive,--radius`.
- HydraHive-Box: `--hh-bg(#0b0e16), --hh-panel(#1c2334), --hh-panel-top, --hh-panel-bot, --hh-bd, --hh-r(1.1rem)`.
- Theme-Akzent: `--hh-accent-from/-to/-/-text/-soft/-border`, `--hh-scrollbar-thumb(/-hover)`.

### Konfig / localStorage-Keys / Env

- `hh-theme` (theme.ts) — gewähltes Theme.
- `hh2.lang` (i18n) — Sprache (LanguageDetector).
- `hh2.chat.panels` (ThreePanelLayout) — `{left,right}` Panel-Sichtbarkeit.
- `hh_landing` (LandingSwitcher) — `buddy|dashboard` Startseite.
- `hh_tts_provider` / `hh_tts_voice` (useVoiceOutput) — TTS-Provider + Stimme; `DEFAULT_VOICE="German_FriendlyMan"`.
- Backend-Pfad-Konstanten in Regexen: Media nur unter `/tmp` bzw. `/var/lib/hydrahive2` (`MediaPreview.tsx:24-30`).
- Schwellen-Konstanten: `MAX_FILES=5`, `MAX_IMAGE_BYTES=5MB`, `MAX_TEXT_BYTES=100KB` (MessageInput); `COLLAPSE_THRESHOLD_CHARS=300`/`_LINES=8` (ToolCards); `WARN_THRESHOLD=20000`/`FRESH_BASELINE=10000` (NewChatHint).

### Konsumierte Backend-Endpoints (Vertrag)

- `GET/POST /sessions`, `GET/PATCH/DELETE /sessions/{id}`, `POST /sessions/{id}/tool-confirm/{call_id}`.
- `GET /sessions/{id}/messages`, `POST /sessions/{id}/messages` (SSE), `POST /sessions/{id}/messages/{mid}/resend`, `GET /sessions/{id}/tokens`, `POST /sessions/{id}/compact`, `POST /sessions/{id}/log-cmd`.
- `GET /workspace/tree|file|raw|git/repos|git/status|git/diff`, `PUT /workspace/file`, `POST /workspace/git/stage|git/commit`.
- `GET /files?path=&token=`, `POST /stt`, `POST /tts`, `GET /tts/voices`.
- `GET /health`, `GET /system/check-update`, `POST /system/update`, `GET /system/update/log`, `POST /system/restart`.
- `GET /agents`, `GET /projects`, `GET /llm/effort-models`, plus `agentsApi.getModels/getSystemPrompt/listTools/update`, `skillsApi.list`.

---

## Offene Enden

- **Tote Datei `_Thread.tsx`** (`features/chat/_Thread.tsx`): `HydraThread` + `HydraUserMessage`/`HydraAssistantMessage`/`HydraSystemMessage` sind nirgends importiert (Grep bestätigt). Es ist der Vorgänger des aktiven `_ChatBubbleThread.tsx` (Gradient-Bubble-Look vs. Card-Look). Verwendet noch `(b as any)` (`:90`). Kandidat zum Löschen.
- **Doppelte `PendingConfirm`-Definition**: einmal in `useChat.ts:6`, einmal in `ToolConfirmBanner.tsx:4` — identische Felder, keine geteilte Quelle. DRY-Bruch; sollte aus `types.ts` kommen.
- **`CompactionBlock` Inkonsistenz Tokens-Label**: Memory + Code nennen das Feld `tokensBefore` als „Tokens gespart", aber inhaltlich ist es der Stand **vor** Compaction (Naming irreführend; UI-Text „gespart" vs. Feldname `tokensBefore`).
- **`/devchat` Redirect-Altlast** (`App.tsx:71`): alter Routenname permanent auf `/werkstatt` umgeleitet — kann perspektivisch raus, sobald keine alten Links/Bookmarks mehr existieren.
- **`HelpTopic` deckt nur 7 Themen ab** (`help/loader.ts:4`): nur `dashboard/chat/agents/projects/llm/mcp/system` haben Hilfe-Markdown (`help/de|en/*.md`). Alle anderen Seiten (Butler, Containers, Health, …) haben **keinen** `HelpButton`-Inhalt; `loadHelp` liefert dort den Platzhalter „_Hilfe für dieses Thema fehlt noch._".
- **`nav.json` enthält `items.chat` und `items.wiki`** (Locale-Keys vorhanden), aber es gibt **keine** Route `/chat` (durch `/werkstatt` ersetzt) und **kein** `/wiki` in `NAV_ITEMS`/`App.tsx`. Verwaiste Übersetzungs-Keys.
- **`workspace.json` hat `tab_editor`/`empty`/`stage_all`** Keys, die in den aktuellen Workspace-Komponenten nicht (mehr) referenziert werden (`WorkspacePanel` nutzt nur `tab_files`/`tab_git`). Vermutlich Reste eines früheren Editor-Tabs.
- **`useChat.confirmTool` rendert keine optimistische UI**: `pendingConfirm` wird nach Approve/Deny sofort genullt, aber der eigentliche Tool-Lauf kommt erst über den weiterlaufenden Stream zurück — wenn der Stream zwischenzeitlich endete, bliebe der Banner-State potenziell hängen (Edge-Case, da der Stream normalerweise offen bleibt).
- **`CollapsibleSidebar` vs. `CollapsiblePanel`**: zwei unabhängige Einklapp-Mechanismen (Shell-weit vs. Chat-intern) mit ähnlicher Logik — bewusst getrennt, aber konzeptuell redundant.
- **`MediaPreview` Doppel-Pfad (Regex + strukturiert)**: der Regex-Extraktor ist laut Header nur noch Fallback für alte Sessions/Freitext; solange beide existieren, müssen Pfad-Konstanten (`/tmp`,`/var/lib/hydrahive2`) an zwei Stellen (hier + Backend `files.py`) konsistent bleiben.
- **Effort-Support-Heuristik teils hardcoded** (`SessionModelControls.tsx:25-26`): `isClaudeModel || /^MiniMax-M2/` bestimmt, ob die Effort-Pill **überhaupt** erscheint — das ist eine separate, frontend-lokale Liste neben dem SSOT-`/llm/effort-models` (der nur xhigh/max steuert). Drift-Risiko, wenn ein neues Reasoning-Modell dazukommt.
- **`App.css`** existiert noch im `src/`-Root (Vite-Template-Rest), wird aber von `main.tsx` nicht importiert (nur `index.css`). Toter Stylesheet-Kandidat.
- **`pricing.ts` ist hardgecodete Preistabelle** (Stand 2026-Q1) — bewusst lokal, aber driftet zwangsläufig gegen reale Provider-Preise; nur für die UI-Kostenschätzung (`AssistantFooter`), nicht abrechnungsrelevant.
