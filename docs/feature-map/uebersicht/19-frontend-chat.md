# Feature Map: Frontend Chat UI

> **Pfad:** `frontend/src/features/chat/`  
> **Was:** Die Haupt-Chat-Oberfläche. Messages, Tool-Cards, Emotes, Voice, Workspace.  
> **Warum:** Das ist was der User täglich sieht und bedient.

---

## Dateien

### Seiten & Layout
| Datei | Verantwortung |
|---|---|
| `ChatPage.tsx` | Haupt-Seite. Three-Panel-Layout: SessionList + Chat + Workspace. |
| `layout/ThreePanelLayout.tsx` | Drei-Spalten-Layout mit konfigurierbaren Breiten |
| `layout/CollapsiblePanel.tsx` | Einklappbare Panel-Komponente |
| `_ChatHeader.tsx` | Obere Leiste: Agent-Name, Modell, Token-Meter, Settings |
| `_Thread.tsx` | Message-Thread — rendert alle Bubbles |
| `_ChatBubbleThread.tsx` | Einzelne Bubble mit User/Assistant-Styling |

### Message-Input
| Datei | Verantwortung |
|---|---|
| `MessageInput.tsx` | Textarea + Send-Button + Slash-Commands + File-Attach + Voice-Input |
| `commands.ts` | Slash-Command-Definitionen (`/model`, `/compact`, `/clear`, ...) |
| `useChat.ts` | **Haupt-State-Hook.** Session-State, Message-Sending, SSE-Stream |
| `useChatCompact.ts` | Compaction-Trigger aus dem Chat |
| `useVoiceInput.ts` | Mikrofon → STT → Text in Input |
| `useVoiceOutput.ts` | TTS: Assistant-Antworten vorlesen |
| `_chatStream.ts` | SSE-Stream-Verarbeitung, Event-Parsing |
| `_assistantRuntime.ts` | Assistant-SDK-Runtime-Integration |

### Sessions
| Datei | Verantwortung |
|---|---|
| `SessionList.tsx` | Linke Sidebar: Session-Liste, Suche, Neu-erstellen |
| `NewSessionDialog.tsx` | Dialog: neue Session erstellen (Agent/Modell wählen) |
| `ChatSearchBar.tsx` | Volltext-Suche über Session-History |
| `ChatSearchContext.tsx` | Search-Context-Provider |

### Markdown & Rendering
| Datei | Verantwortung |
|---|---|
| `Markdown.tsx` | Markdown-Renderer (react-markdown + Plugins) |
| `remarkHydraEmotes.ts` | remark-Plugin: `:hydra-NAME:` → `<img>` |
| `hydraEmotes.ts` | Emote-Name → URL Mapping |
| `_emoteNames.generated.ts` | Auto-generierte Liste aller Emote-Namen |
| `EmoteText.tsx` | Text mit Emotes rendern |
| `EmotePicker.tsx` | Emoji-Picker für Hydra-Emotes im Input |
| `ThinkingBlock.tsx` | Extended-Thinking-Blöcke anzeigen (klappbar) |
| `CompactionBlock.tsx` | Compaction-Summary im Thread anzeigen |
| `BubbleMeta.tsx` | Bubble-Footer: Modell, Token-Usage, Dauer, Kosten |

### Tool-Cards
| Datei | Verantwortung |
|---|---|
| `ToolCards.tsx` | Dispatch: welche Tool-Card für welchen Tool-Call? |
| `tool_cards/ShellExecCard.tsx` | shell_exec: Command + Output anzeigen |
| `tool_cards/GitDiffCard.tsx` | git diff: Diff-Ansicht mit Syntax-Highlighting |
| `tool_cards/WebSearchCard.tsx` | web_search: Suchergebnisse mit Links |

### Media & Dateien
| Datei | Verantwortung |
|---|---|
| `MediaPreview.tsx` | Bild/Video/Audio-Preview im Chat |
| `ImageLightbox.tsx` | Fullscreen-Bild-Ansicht |
| `EpubViewer.tsx` | EPUB-Bücher direkt im Chat lesen |
| `_MessageFileChip.tsx` | Datei-Chip im Message-Input (attached files) |

### Modell & Settings
| Datei | Verantwortung |
|---|---|
| `ModelPicker.tsx` | Modell-Auswahl (Such-Combobox, 🆓-Badge, Custom-Eintrag) |
| `SessionModelControls.tsx` | Per-Session Modell-Override |
| `ReasoningEffortPill.tsx` | Reasoning-Effort Pill (low/medium/high) |
| `TokenMeter.tsx` | Token-Usage-Anzeige (Context-Window-Auslastung) |
| `pricing.ts` | Client-seitige Preis-Berechnung |

### Sonstiges
| Datei | Verantwortung |
|---|---|
| `NewChatHint.tsx` | Hint wenn keine Sessions vorhanden |
| `ToolConfirmBanner.tsx` | Tool-Confirm-Banner (wenn Agent Tool-Bestätigung braucht) |
| `AgentPixelMonitor.tsx` | Debug: Agent-Pixel-Status |
| `_SkillCatalogPill.tsx` | Skill-Auswahl-Pill im Input |
| `_mcCharacters.ts` | Minecraft-Characters (für hyos-Integration) |
| `api.ts` | Alle Chat-API-Calls |
| `types.ts` | TypeScript-Typen für Messages, Sessions, etc. |

### Workspace-Panel
| Datei | Verantwortung |
|---|---|
| `workspace/WorkspacePanel.tsx` | Rechte Sidebar: Datei-Browser + Editor + Git |
| `workspace/FileTree.tsx` | Dateibaum mit Icons |
| `workspace/FileEditor.tsx` | Monaco-Editor für Dateien |
| `workspace/FileOverlay.tsx` | Fullscreen-Editor-Overlay |
| `workspace/GitPanel.tsx` | Git-Status, Commit, Push |
| `workspace/MediaViewer.tsx` | Bilder/Videos im Workspace anzeigen |
| `workspace/monacoSetup.ts` | Monaco-Editor Konfiguration (Themes, Languages) |
| `workspace/useWorkspace.ts` | Workspace-State-Hook |
| `workspace/fileType.ts` | Dateityp-Erkennung (→ Icon, Editor-Modus) |
| `workspace/api.ts` | Workspace API-Calls |

---

## SSE-Stream-Verarbeitung

```
POST /api/chat/sessions/{id}/messages
  → Response: SSE-Stream

Events die ankommen:
  message_start  → Neue Bubble anlegen
  text_delta     → Text-Streaming in Bubble
  text_block     → Fertiger Text-Block
  tool_use       → Tool-Card anzeigen
  tool_result    → Tool-Ergebnis in Card
  thinking_block → Thinking-Block (klappbar)
  token_usage    → Token-Meter updaten
  done           → Stream beendet
  error          → Fehler-Bubble
```

---

## Hydra-Emotes im Frontend

```
remarkHydraEmotes.ts:
  :hydra-smile: → <img src="/illustrations/emoticons/hydra-smile.png" class="hydra-emote">

hydraEmotes.ts:
  EMOTE_MAP = {
    "smile": "/illustrations/emoticons/hydra-smile.png",
    "grin": "/illustrations/emoticons/hydra-grin.png",
    ... (159 Einträge)
  }

_emoteNames.generated.ts:
  export const EMOTE_NAMES = ["smile", "grin", "lol", ...] // auto-generiert
```

Emote-Bilder liegen in `frontend/public/illustrations/emoticons/`.

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): SSE-Events kommen vom Runner
- **→ Streaming** (`22-streaming.md`): SSE-Transport-Details
- **→ Buddy** (`09-buddy.md`): BuddyPage ist ähnlich aufgebaut
- **→ Voice** (`29-voice.md`): useVoiceInput/useVoiceOutput
