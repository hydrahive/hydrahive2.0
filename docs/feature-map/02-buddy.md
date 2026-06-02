# Buddy

> Subsystem-Doku für die Feature-Landkarte. Stand: 2026-06-02 (main).
> Buddy = der persönliche, dauerhafte Chat-Kumpel pro HydraHive-User. Technisch
> ein **ganz normaler Master-Agent** mit dem Marker `is_buddy=True` im Config,
> einer fortlaufenden **Lifetime-Session** und einem zufällig gewürfelten
> **Fiktiv-Charakter** als Rollen-Färbung. Auto-erstellt beim ersten Aufruf der
> Buddy-Page. Slash-Commands laufen **deterministisch ohne LLM-Roundtrip**.

---

## WAS

### Backend — Python-Module (`core/src/hydrahive/buddy/`)

#### `__init__.py` — Auto-Create + Lifetime-Session + Soul-Builder
- **`_TONE_DESC`** (Dict) — 3 Ton-Beschreibungen: `locker`, `professionell`, `knapp`. Wird in den Soul-Prompt eingebaut.
- **`_LANG_DESC`** (Dict) — 3 Sprach-Beschreibungen: `de` ("Du sprichst immer Deutsch"), `en` ("You always respond in English"), `auto` ("Du sprichst die Sprache in der der User schreibt").
- **`_build_soul(username, universe, character, language="de", tone="locker", context="")`** — baut den kompletten Soul-System-Prompt aus fertig gewähltem Charakter + Universum + Ton + Sprache + optionalem User-Kontext. Kein LLM-Bootstrap.
- **`_init_universe`, `_init_char`** — Modul-Level-Würfelwurf beim Import (Backwards-compat-Build).
- **`BUDDY_SOUL`** — Modul-Level-Konstante: ein initialer Soul mit Platzhalter-Username `"PLACEHOLDER"`. Exportiert, aber praktisch tot (siehe Offene Enden).
- **`_find_buddy_for(username) -> dict | None`** — sucht unter allen Agents des Users den ersten mit `is_buddy=True`.
- **`_get_or_create_session(agent_id, username) -> str`** — Lifetime-Session: nimmt die jüngste existierende Session des Buddy-Agents (sortiert nach `created_at` desc), erstellt eine neue wenn keine da.
- **`get_or_create_buddy(username) -> dict`** — Kern-Entrypoint. Erstellt bei Bedarf einen Master-Agent, würfelt Charakter, legt Memory-Key `character` an, erstellt Lifetime-Session. Returnt `{agent_id, session_id, agent_name, model, created}`.
- **`__all__ = ["get_or_create_buddy", "BUDDY_SOUL"]`**

#### `_characters.py` — Charakter-Katalog + Würfel
- **`_UNIVERSE_CHARACTERS`** (Dict[str, list[str]]) — 39 fiktive Universen mit je 5–10 Nebenfiguren (Star Wars, Star Trek, Herr der Ringe, Game of Thrones, Marvel, DC, Disney, Pixar, Studio Ghibli, One Piece, Naruto, Cowboy Bebop, JoJo, Griechische/Nordische Mythologie, Brüder Grimm, Sherlock Holmes, Discworld, Hitchhiker's Guide, Doctor Who, Witcher, BioWare, Final Fantasy, Zelda, Dune, Cyberpunk, Stranger Things, Breaking Bad, Asterix, Tim und Struppi, Shakespeare, Bibel).
- **`pick_character() -> tuple[str, str]`** — würfelt deterministisch in Python (`random.choice`) Universum + Name. Bewusst Nebenfiguren statt Hauptfiguren.

#### `commands.py` — Slash-Command-Logik (deterministisch, kein LLM)
- **`_require_buddy(username) -> dict`** — wirft `LookupError` wenn kein Buddy existiert.
- **`clear_session(username)`** → `/clear` + `/reset`: beendet aktuelle Lifetime-Session, legt neue an. Alte bleibt in DB.
- **`remember(username, text=None, name=None)`** → `/remember`: schreibt Memory-Eintrag ohne LLM. 3 Modi (Snapshot der aktiven Session / freie Notiz / benannte Notiz).
- **`list_models(username)`** → `/model` ohne Arg: aktuelles + verfügbare Modelle (live aus Katalog-Cache via `_available_models()`).
- **`set_model(username, model)`** → `/model <name>`: wechselt LLM-Modell, validiert via `validate_model`.
- **`reroll_character(username)`** → `/character`: würfelt neuen Charakter, schreibt in Memory + System-Prompt + neue Lifetime-Session.

#### `_commands_helpers.py` — interne Helper (kein LLM)
- **`_SLUG_RE`** — Regex `[^a-z0-9_-]+` für Key-Slugging.
- **`slug(s)`** — normalisiert einen freien Namen auf einen Memory-Key (Fallback `"note"`).
- **`extract_text_from_content(content)`** — extrahiert Text-Teile aus DB-Message-Content (str oder list[ContentBlock]).
- **`snapshot_active_session(buddy, username, last_n=30)`** — Markdown-Dump der letzten N User/Assistant-Messages der aktiven Buddy-Session.

#### `_config.py` — Settings-Page-Backend (Config lesen/schreiben)
- **`_find_buddy(username) -> dict`** — wie `_find_buddy_for`, aber wirft `LookupError`.
- **`get_config(username) -> dict`** — liefert alle Settings: `name`, `model`, `character`, `tools`, `all_tools` (Core-Registry + Plugin-Tools), `compact_threshold_pct`, `compact_model`, `tool_result_max_chars`, `language`, `tone`, `context`.
- **`patch_config(username, changes) -> dict`** — wendet Teiländerungen an. Baut Soul neu + erstellt neue Session wenn `language`/`tone`/`context` ändern (`soul_dirty`). Returnt `{ok, new_session_id}`.

### Backend — API-Endpoints (`core/src/hydrahive/api/routes/buddy.py`, prefix `/api/buddy`)
- **`GET /api/buddy/state`** → `buddy_state` → ruft `get_or_create_buddy`. Auto-create bei erstem Aufruf.
- **`POST /api/buddy/clear`** → `buddy_clear` → `commands.clear_session`. 404 `buddy_not_found`.
- **`POST /api/buddy/remember`** (Body `RememberBody{text?, name?}`) → `buddy_remember` → `commands.remember`. 404 / 400.
- **`GET /api/buddy/models`** → `buddy_models` → `commands.list_models`.
- **`POST /api/buddy/model`** (Body `ModelBody{model}`) → `buddy_model` → `commands.set_model`.
- **`POST /api/buddy/character`** → `buddy_character` → `commands.reroll_character`.
- **`POST /api/buddy/log-cmd`** (Body `LogCmdBody{user_text, assistant_text}`) → `buddy_log_cmd`: persistiert Slash-Command-Output als sichtbare User-/Assistant-Bubble in die aktive Session (Metadata `source: "slash_command"`).
- **`GET /api/buddy/config`** → `get_buddy_config` → `buddy_config.get_config`.
- **`PATCH /api/buddy/config`** (Body `BuddyConfigPatch`) → `patch_buddy_config` → `buddy_config.patch_config`.

### Backend — Runner-Integration (`is_buddy`-Marker)
- **`with_emote_hint(base_prompt, is_buddy)`** (`runner/_emote_hint.py`) — hängt NUR beim Buddy den Hydra-Emote-Hinweis an den System-Prompt an (zur Laufzeit, nicht in den editierbaren Prompt gebacken).
- **`HYDRA_EMOTE_HINT`** — der angehängte Text-Block: erlaubt `:hydra-NAME:`-Emoticons.
- **`EMOTE_NAMES`** — ~145 Emote-Namen (Gesichter, Symbole, Objekte), spiegelt `EMOTE_NAMES` aus dem Frontend.

### Frontend — Komponenten (`frontend/src/features/buddy/`)

#### `BuddyPage.tsx` — Haupt-Chat-Seite (3-Spalten-Layout)
- **`BuddyPage()`** — orchestriert State, Chat-Hook, TTS, Runtime, Slash-Command-Dispatch.
- **Mittlere Spalte:** Buddy-Mascot-Header (HydraMascot, Agent-Name, `ModelPicker`, `ReasoningEffortPill`, Settings-Button, Neuer-Chat-Button), `NewChatHint`, `BuddyThread`, `ToolConfirmBanner`, `MessageInput` mit QuickAction-Pills. Stilistisch als "Gerät" mit Standfuß gerendert (abgerundeter Kasten + ON-LED unten rechts + Sockel-Divs).
- **`appendLocal(role, text)`** — fügt lokale (nicht-persistierte) Message hinzu (`local-cmd-…` ID).
- **`handleSend(text, files)`** — Slash-Command-Routing: erkennt `/`-Befehl → lokale Anzeige → `runCommand` → ggf. Session-Wechsel oder `logCmd`-Persistierung.
- **QuickAction-Pills (CmdPill):** `help`, `clear`, `remember`, `model` (insert statt run), `character`, `compact`, `system`, `agent`, `soul`, `export`.
- **Linke Spalte (`xl:`):** `BuddyLeftPanel`.
- **Rechte Spalte (`xl:`):** `BuddyExtensionsPanel` + `HealthBuddyBox`.

#### `_BuddyLeftPanel.tsx` — linke Info-Spalte (nur ab `xl`)
- **`PanelBox`** — generischer Karten-Wrapper mit `--c`-Akzentfarbe.
- **`StatRow`** — Label/Value-Zeile.
- **`ZahnfeeBox`** — zeigt das tägliche Zahnfee-Briefing (🦷): 4 Sektionen (Offen/Gut/Schlecht/Heute) + Link `/zahnfee`. Lade-/Leer-/Error-States.
- **`BuddyLeftPanel`** — kombiniert `ZahnfeeBox` + System-Box (Tokens heute, aktive Sessions, Tool Calls, Server, Backend-Status aus `dashboardApi.summary()`).

#### `_BuddyExtensionsPanel.tsx` — rechte "Anwendungen"-Spalte
- **`ICON_MAP`** — Lucide-Icon-Mapping nach Name-String.
- **`ExtIcon`** — Icon mit Package-Fallback.
- **`ExtTile`** — eine Extension-Kachel (Status-LED, Open-URL-Link in neuem Tab, Docker-/Plain-Open-URL-Auflösung).
- **`BuddyExtensionsPanel`** — lädt installierte Extensions (`fetchExtensions().filter(installed)`), 3-Spalten-Grid (🧩).

#### `_BuddyThread.tsx` — Message-Thread (assistant-ui)
- **`BuddyUserMessage`** — User-Bubble (Bot-Icon rechts), Edit/Copy-Actions, separates Rendering von Tool-Results.
- **`BuddyAssistantMessage`** — Assistant-Bubble (HydraMascot links), Markdown/Mono-Mode (Slash-Output mono), TTS-Button, Copy, Reload, Raw-JSON-Toggle, Branch-Picker, MediaPreview.
- **`BuddySystemMessage`** — rendert nur `compaction`-Messages via `CompactionBlock`.
- **`BuddyThread`** — `ThreadPrimitive` mit Empty-State ("Frische Tentakel, frischer Chat").

#### `_BuddyCmdPill.tsx` — QuickAction-Pill
- **`PILL_COLORS`** — 5 Farb-Varianten (sky/amber/emerald/violet/pink).
- **`CmdPill`** — kleiner Slash-Command-Button. Wird auch von der Chat-Page (`werkstatt`) re-importiert.

#### `BuddySettingsPage.tsx` — Settings-Seite (`/buddy/settings`)
- **`BuddySettingsPage()`** — 4-Tab-Container (Identität/Kontext/Tools/Kompaktierung), Draft-State, Save-Logik. Nach Save mit `new_session_id` → Auto-Navigate nach `/` (1.2s Delay).
- **`applyDraft(patch)`** — merge in Draft.
- **`save()`** — `patchConfig(draft)` → reload Config → ggf. Navigate.
- **`handleReroll()`** — `buddyApi.character()` → reload → Navigate `/` (0.8s).

#### `_BuddySettingsIdentity.tsx` — Tab "Identität"
- Name-Input, Charakter-Anzeige + Reroll-Würfel-Button (🎲), Sprach-Select (de/en/auto), Ton-Select (locker/professionell/knapp).

#### `_BuddySettingsContext.tsx` — Tab "Kontext"
- Textarea (max 8000 Zeichen) "Was soll Buddy über dich wissen?". Wird in jeden Chat injiziert. Hinweis: Änderung startet neue Session.

#### `_BuddySettingsTools.tsx` — Tab "Tools"
- Toggle-Grid aller Tools (`all_tools`), "Alle an"/"Alle aus", aktive Anzahl. Schreibt `tools`-Liste.

#### `_BuddySettingsCompaction.tsx` — Tab "Kompaktierung"
- Compaction-Trigger-Slider (20–95%, step 5), Compact-Modell-Select (leer = Hauptmodell), Tool-Result-Limit-Number (0 = kein Limit, Empfehlung 12000).

#### `api.ts` — Frontend-API-Client
- **Typen:** `BuddyState`, `ClearResult`, `RememberResult`, `ModelsResult`, `SetModelResult`, `CharacterResult`, `BuddyConfig`, `BuddyConfigPatch`, `PatchResult`.
- **`buddyApi`** — `state`, `clear`, `remember`, `models`, `setModel`, `character`, `logCmd`, `getConfig`, `patchConfig`.

#### `commands.ts` — Frontend-Slash-Command-Dispatcher
- **`HELP_TEXT`** — Hilfetext für `/help`.
- **`isCommand(text)`** — `text.trimStart().startsWith("/")`.
- **`runCommand(text, state)`** — Switch über alle Befehle.
- Befehl-Helper: **`modelCmd`**, **`compactCmd`**, **`tokensCmd`**, **`titleCmd`**, **`systemCmd`**, **`toolsCmd`**, **`agentCmd`**, **`soulCmd`**, **`exportCmd`**.

### Slash-Commands (vollständige Liste)
| Command | Aliase | Backend-Roundtrip | Effekt |
|---|---|---|---|
| `/help` | — | nein (lokal) | zeigt `HELP_TEXT` |
| `/clear` | `/reset` | `POST /buddy/clear` | neue Lifetime-Session, Session-Wechsel |
| `/remember [name]` | — | `POST /buddy/remember` | Memory-Eintrag (Snapshot/Notiz) |
| `/model [name]` | `/models` | `GET`/`POST /buddy/model` | Modell anzeigen/wechseln |
| `/character` | — | `POST /buddy/character` | Charakter neu würfeln, Session-Wechsel |
| `/compact` | — | `chatApi.compact(session_id)` | manuelle Compaction |
| `/tokens` | — | `chatApi.tokens(session_id)` | Token-Stand + Window-% |
| `/title <text>` | `/rename` | `chatApi.updateSession` | Session umbenennen |
| `/system` | `/sys` | `agentsApi.getSystemPrompt` | System-Prompt anzeigen |
| `/tools` | — | `agentsApi.listTools` | Backend-Tools auflisten |
| `/agent` | — | nein (aus `state`) | Agent-Info (id/Modell/Session) |
| `/soul` | — | `agentsApi.getSoul` | Soul-Komponenten (⚠ admin-only) |
| `/export` | — | `chatApi.listMessages` | Verlauf als Markdown |

---

## WIE

### Erst-Aufruf / Auto-Create
1. User landet auf `/` und hat als Landing "buddy" gewählt (`getLanding()`) ODER navigiert auf Buddy-Page (`App.tsx:63`). `BuddyPage` mountet.
2. `useEffect` (einmalig via `initRef`) ruft `buddyApi.state()` → `GET /api/buddy/state`.
3. Backend `buddy_state` ruft `get_or_create_buddy(username)`:
   - `_find_buddy_for(username)` scannt `agent_config.list_by_owner(username)` nach `is_buddy=True`.
   - **Existiert:** falls `compact_threshold_pct > 70` → auf 70 zurücksetzen; Lifetime-Session holen/erstellen; `created=False`.
   - **Existiert nicht:** Default-Modell aus `load_config()` (oder erstes Provider-Modell, Fallback `claude-sonnet-4-6`); `pick_character()` würfelt Universum+Figur; `_build_soul` baut Soul; `agent_config.create(agent_type="master", …, temperature=1.0, max_tokens=16000, thinking_budget=0)`; `agent_config.update(is_buddy=True, compact_threshold_pct=70)`; `memory_store.write_key(agent_id, "character", "<Figur> (aus <Universum>)")`; Session anlegen; `created=True`.
4. Frontend setzt `state`; `useEffect` auf `state.session_id` triggert `chat.reload()` → lädt Messages der Lifetime-Session.
5. Bei `created=True` zeigt die Page kurz "🎉 frisch geschlüpft".

### Normale Chat-Nachricht
1. `MessageInput.onSend` → `handleSend(text, files)`.
2. `isCommand(text)` false → `chat.send(text, files)` (Standard-Chat-Hook → SSE-Runner-Loop wie jeder Master-Agent).
3. Runner (`runner.py:95–96`) holt `base_system_prompt` und ruft `with_emote_hint(prompt, is_buddy=True)` → hängt Hydra-Emote-Block an (nur Buddy).

### Slash-Command-Fluss (deterministisch)
1. `handleSend` erkennt `/`-Präfix.
2. `appendLocal("user", text)` → sofortige lokale Anzeige (kein Spinner).
3. `runCommand(text, state)`:
   - Parsen: `cmd` = erstes Token (lowercased), `arg` = Rest.
   - Switch → entweder lokal (`/help`, `/agent`) oder REST/`chatApi`/`agentsApi`.
4. `appendLocal("assistant", result.message)`.
5. **Session-wechselnde Befehle** (`/clear`, `/character` mit `result.newSessionId`): `setLocalMsgs([])`, `setState(session_id=neu)` → `useEffect` reload. **Return** (kein Persistieren — neue Session ist leer).
6. **Andere Befehle:** `buddyApi.logCmd(text, message)` persistiert User+Assistant-Bubble (Metadata `slash_command`); danach `chat.reload()` + `setLocalMsgs([])`. Bei Persistenz-Fehler bleibt `localMsgs` als Fallback bis zum nächsten reload.

### `/remember`-Logik (3 Modi, `commands.py:remember`)
- **text leer + name leer:** `snapshot_active_session` (letzte 30 User/Assistant-Messages als Markdown) → Key `session_<YYYY-MM-DD>` (bei Kollision `_HHMMSS`-Suffix). Inhalt mit `# Session <Datum>`-Header.
- **name gegeben (mit/ohne text):** Key = `slug(name)`.
- **text gegeben, kein name:** Key = `note_<unix>`.
- Frontend ruft `/remember` aber nur mit `{name}` ODER `{}` auf (nie mit freiem `text` — der `text`-Pfad ist nur via direkte API erreichbar).

### Charakter-Reroll (`/character`, `reroll_character`)
1. `pick_character()` → neues (Universum, Figur).
2. `memory.write_key(bid, "character", "<Figur> (aus <Universum>)")`.
3. `_build_soul(username, universe, character)` (Default-Sprache/Ton/Kontext! — siehe Gotchas) → `agent_config.set_system_prompt`.
4. Neue Lifetime-Session anlegen → `session_id` zurück → Frontend wechselt Session.

### Settings-Patch (`patch_config`)
1. `PATCH /buddy/config` mit `model_dump(exclude_none=True)`.
2. Felder split: `name`/`tools` → `agent_updates`; `compact_*`/`tool_result_max_chars` → `agent_updates`; `language`/`tone`/`context` → Memory-Keys `_pref_language`/`_pref_tone`/`_pref_context` + `soul_dirty=True`.
3. `agent_config.update(bid, **agent_updates)`.
4. Wenn `soul_dirty`: aktuellen Charakter aus Memory parsen (`"<Figur> (aus <Universum>)"`), Prefs lesen, `_build_soul(...)` mit allen 6 Args, `set_system_prompt`, **neue Session** anlegen → `new_session_id` zurück → Frontend navigiert nach `/`.

### Soul-Aufbau (`_build_soul`)
Template-String: "Du bist **{character}** aus **{universe}** — und gleichzeitig {username}'s persönlicher Buddy." + Rollen-Konsistenz-Anweisung + Ton (`_TONE_DESC[tone]`) + Sprache (`_LANG_DESC[language]`) + Tool-Verfügbarkeit + Memory-Tool-Hinweis + (optional) `## Kontext über {username}\n{context}`.

---

## WO

### Backend
- `core/src/hydrahive/buddy/__init__.py:19` — `_TONE_DESC`
- `core/src/hydrahive/buddy/__init__.py:24` — `_LANG_DESC`
- `core/src/hydrahive/buddy/__init__.py:31` — `_build_soul(username, universe, character, language, tone, context)`
- `core/src/hydrahive/buddy/__init__.py:61` — `_init_universe`, `_init_char` (Import-Zeit-Würfel)
- `core/src/hydrahive/buddy/__init__.py:62` — `BUDDY_SOUL` (Platzhalter-Konstante)
- `core/src/hydrahive/buddy/__init__.py:65` — `_find_buddy_for(username)`
- `core/src/hydrahive/buddy/__init__.py:72` — `_get_or_create_session(agent_id, username)`
- `core/src/hydrahive/buddy/__init__.py:84` — `get_or_create_buddy(username)`
- `core/src/hydrahive/buddy/__init__.py:96-97` — Threshold-Clamp `>70 → 70` (existierender Buddy)
- `core/src/hydrahive/buddy/__init__.py:114-125` — `agent_config.create(...)` (master, temp 1.0, max_tokens 16000, thinking_budget 0)
- `core/src/hydrahive/buddy/__init__.py:126` — `update(is_buddy=True, compact_threshold_pct=70)`
- `core/src/hydrahive/buddy/__init__.py:127-130` — `memory_store.write_key(agent_id, "character", ...)`
- `core/src/hydrahive/buddy/__init__.py:142` — `__all__`
- `core/src/hydrahive/buddy/_characters.py:6` — `_UNIVERSE_CHARACTERS` (39 Universen)
- `core/src/hydrahive/buddy/_characters.py:42` — `pick_character()`
- `core/src/hydrahive/buddy/commands.py:19` — `_require_buddy(username)`
- `core/src/hydrahive/buddy/commands.py:26` — `clear_session(username)`
- `core/src/hydrahive/buddy/commands.py:40` — `remember(username, text, name)`
- `core/src/hydrahive/buddy/commands.py:76` — `list_models(username)`
- `core/src/hydrahive/buddy/commands.py:83` — `set_model(username, model)`
- `core/src/hydrahive/buddy/commands.py:98` — `reroll_character(username)`
- `core/src/hydrahive/buddy/_commands_helpers.py:9` — `_SLUG_RE`
- `core/src/hydrahive/buddy/_commands_helpers.py:12` — `slug(s)`
- `core/src/hydrahive/buddy/_commands_helpers.py:16` — `extract_text_from_content(content)`
- `core/src/hydrahive/buddy/_commands_helpers.py:31` — `snapshot_active_session(buddy, username, last_n=30)`
- `core/src/hydrahive/buddy/_config.py:11` — `_find_buddy(username)` (wirft `LookupError`)
- `core/src/hydrahive/buddy/_config.py:18` — `get_config(username)`
- `core/src/hydrahive/buddy/_config.py:40` — `patch_config(username, changes)`
- `core/src/hydrahive/buddy/_config.py:57-60` — Compact-Felder-Durchschleifen
- `core/src/hydrahive/buddy/_config.py:61-71` — Pref-Keys schreiben + `soul_dirty`
- `core/src/hydrahive/buddy/_config.py:76-92` — Soul-Rebuild + neue Session

### API-Routes
- `core/src/hydrahive/api/routes/buddy.py:18` — `router = APIRouter(prefix="/api/buddy")`
- `core/src/hydrahive/api/routes/buddy.py:21` — `GET /state` → `buddy_state`
- `core/src/hydrahive/api/routes/buddy.py:27` — `_user(auth)`
- `core/src/hydrahive/api/routes/buddy.py:31` — `POST /clear` → `buddy_clear`
- `core/src/hydrahive/api/routes/buddy.py:39` — `RememberBody` (text ≤4000, name ≤80)
- `core/src/hydrahive/api/routes/buddy.py:44` — `POST /remember` → `buddy_remember`
- `core/src/hydrahive/api/routes/buddy.py:57` — `GET /models` → `buddy_models`
- `core/src/hydrahive/api/routes/buddy.py:65` — `ModelBody` (1–200)
- `core/src/hydrahive/api/routes/buddy.py:69` — `POST /model` → `buddy_model`
- `core/src/hydrahive/api/routes/buddy.py:82` — `POST /character` → `buddy_character`
- `core/src/hydrahive/api/routes/buddy.py:90` — `LogCmdBody` (user_text 1–2000, assistant_text 1–8000)
- `core/src/hydrahive/api/routes/buddy.py:95` — `POST /log-cmd` → `buddy_log_cmd`
- `core/src/hydrahive/api/routes/buddy.py:111-115` — `messages_db.append(...)` user + assistant (metadata `slash_command`)
- `core/src/hydrahive/api/routes/buddy.py:121` — `GET /config` → `get_buddy_config`
- `core/src/hydrahive/api/routes/buddy.py:129` — `BuddyConfigPatch` (Validierungs-Pattern für language/tone)
- `core/src/hydrahive/api/routes/buddy.py:140` — `PATCH /config` → `patch_buddy_config`
- `core/src/hydrahive/api/main.py:18` — `from hydrahive.api.routes.buddy import router as buddy_router`
- `core/src/hydrahive/api/main.py:141` — `app.include_router(buddy_router)`

### Runner / `is_buddy`-Marker
- `core/src/hydrahive/runner/runner.py:95-96` — `base_system_prompt = with_emote_hint(prompt, is_buddy=bool(agent.get("is_buddy")))`
- `core/src/hydrahive/runner/_emote_hint.py:13` — `EMOTE_NAMES`
- `core/src/hydrahive/runner/_emote_hint.py:35` — `HYDRA_EMOTE_HINT`
- `core/src/hydrahive/runner/_emote_hint.py:46` — `with_emote_hint(base_prompt, *, is_buddy)`
- `core/src/hydrahive/agents/_config_utils.py:46` — `cfg.setdefault("is_buddy", False)` (Normalisierung)
- `core/src/hydrahive/agents/_config_utils.py:71` — `list_by_owner(owner)`
- `core/src/hydrahive/agents/_config_utils.py:75` — `get(agent_id)`

### Memory-Store (Backing)
- `core/src/hydrahive/tools/_memory_store.py:1` — Public Facade (re-exports)
- `core/src/hydrahive/tools/_memory_io.py:23` — `_memory_file(agent_id) -> settings.agents_dir/<agent_id>/memory.json`
- `core/src/hydrahive/tools/_memory_io.py:90` — `read_key(agent_id, key)`
- `core/src/hydrahive/tools/_memory_io.py:154` — `write_key(agent_id, key, content, ...)`

### Sessions / Messages DB
- `core/src/hydrahive/db/sessions.py:13` — `class Session` (id, agent_id, project_id, user_id, title, created_at, updated_at, status, metadata)
- `core/src/hydrahive/db/sessions.py:43` — `create(agent_id, user_id, title, project_id, ...)`
- `core/src/hydrahive/db/sessions.py:82` — `list_for_user(user_id, limit=50)`
- `core/src/hydrahive/db/messages.py:13` — `append(session_id, role, content, metadata=None)`

### Frontend
- `frontend/src/App.tsx:25-26` — Imports `BuddyPage`, `BuddySettingsPage`
- `frontend/src/App.tsx:63` — `<Route index … <BuddyPage /> >` (Landing-abhängig)
- `frontend/src/App.tsx:64` — `<Route path="buddy/settings" element={<BuddySettingsPage />} />`
- `frontend/src/features/buddy/BuddyPage.tsx:26` — `BuddyPage()`
- `frontend/src/features/buddy/BuddyPage.tsx:55` — `appendLocal`
- `frontend/src/features/buddy/BuddyPage.tsx:64` — `handleSend`
- `frontend/src/features/buddy/BuddyPage.tsx:203-215` — QuickAction-Pills
- `frontend/src/features/buddy/BuddyPage.tsx:227-230` — rechte Spalte (Extensions + Health)
- `frontend/src/features/buddy/api.ts:3` — `BuddyState`
- `frontend/src/features/buddy/api.ts:17` — `BuddyConfig`
- `frontend/src/features/buddy/api.ts:44` — `buddyApi`
- `frontend/src/features/buddy/commands.ts:16` — `HELP_TEXT`
- `frontend/src/features/buddy/commands.ts:34` — `isCommand`
- `frontend/src/features/buddy/commands.ts:116` — `runCommand`
- `frontend/src/features/buddy/_BuddyThread.tsx:22` — `BuddyUserMessage`
- `frontend/src/features/buddy/_BuddyThread.tsx:74` — `BuddyAssistantMessage`
- `frontend/src/features/buddy/_BuddyThread.tsx:87` — `monoMode = isLocalCmd || isSlashCmd`
- `frontend/src/features/buddy/_BuddyThread.tsx:159` — `BuddySystemMessage`
- `frontend/src/features/buddy/_BuddyThread.tsx:167` — `BuddyThread`
- `frontend/src/features/buddy/_BuddyLeftPanel.tsx:29` — `ZahnfeeBox`
- `frontend/src/features/buddy/_BuddyLeftPanel.tsx:78` — `BuddyLeftPanel`
- `frontend/src/features/buddy/_BuddyExtensionsPanel.tsx:19` — `ExtTile`
- `frontend/src/features/buddy/_BuddyExtensionsPanel.tsx:58` — `BuddyExtensionsPanel`
- `frontend/src/features/buddy/_BuddyCmdPill.tsx:16` — `CmdPill`
- `frontend/src/features/buddy/BuddySettingsPage.tsx:14` — `BuddySettingsPage`
- `frontend/src/features/buddy/_BuddySettingsIdentity.tsx:13` — `BuddySettingsIdentity`
- `frontend/src/features/buddy/_BuddySettingsContext.tsx:9` — `BuddySettingsContext`
- `frontend/src/features/buddy/_BuddySettingsTools.tsx:9` — `BuddySettingsTools`
- `frontend/src/features/buddy/_BuddySettingsCompaction.tsx:10` — `BuddySettingsCompaction`
- `frontend/src/features/chat/ChatPage.tsx:24` — re-import `CmdPill` aus Buddy
- `frontend/src/features/chat/ChatPage.tsx:60` — `buddyAgentIds = agents.filter(is_buddy)`
- `frontend/src/features/chat/ChatPage.tsx:304` — `buddyAgentIds` an SessionList
- `frontend/src/features/chat/types.ts:49` — `is_buddy?: boolean` auf `AgentBrief`
- `frontend/src/features/health/_HealthBuddyBox.tsx:17` — `HealthBuddyBox`
- `frontend/src/features/zahnfee/api.ts:3` — `Briefing`-Typ + `zahnfeeApi`

### i18n
- `frontend/src/i18n/locales/de/buddy.json` — Namespace `buddy` (de)
- `frontend/src/i18n/locales/en/buddy.json` — Namespace `buddy` (en)

---

## WARUM

### Kern-Invarianten / nicht-offensichtliche Verdrahtung
- **Buddy = Master-Agent + Marker.** Es gibt keine eigene Buddy-Tabelle, keine eigene Runner-Logik. Der gesamte Chat läuft durch denselben Runner/Session/Message-Pfad wie jeder andere Agent. Der einzige Unterschied im Runtime-Verhalten: `with_emote_hint` hängt nur beim Buddy den Emote-Block an. Das hält das Subsystem extrem schlank.
- **Genau ein Buddy pro User.** Garantiert nur durch Konvention: `_find_buddy_for` nimmt den **ersten** Agent mit `is_buddy=True`. Es gibt keine DB-Unique-Constraint. Würden zwei Buddy-Agents pro User existieren (z.B. durch parallele Erst-Aufrufe, Race), nähme das System willkürlich einen — der andere wäre Waise. Auto-Create ist nicht atomar/transaktional.
- **Lifetime-Session = "jüngste Session des Buddy-Agents".** `_get_or_create_session` und `snapshot_active_session` definieren "aktiv" konsistent als die nach `created_at` desc neueste Session. `/clear` und `/character` und `patch_config(soul_dirty)` legen jeweils eine **neue** Session an, wodurch die alte automatisch zur Historie wird. Alte Sessions werden nie gelöscht.
- **Charakter wird in Python gewürfelt, NICHT vom LLM.** Die Doku-Strings betonen mehrfach "kein Bootstrap-Tanz mehr" / "kein LLM-Vertrauen mehr". Hintergrund: das LLM würfelte früher selbst und hielt sich nicht zuverlässig an die Wahl. Jetzt steht die Figur deterministisch im System-Prompt + Memory-Key `character`.
- **Charakter-String ist semi-strukturiert:** Format `"<Figur> (aus <Universum>)"`. `patch_config` parst ihn per String-Split (`split("(")` / `split("aus")`) zurück, um beim Soul-Rebuild Figur+Universum zu rekonstruieren — **ohne** neu zu würfeln. Wenn dieser String-Format bricht (z.B. Figur enthält "(" oder "aus"), fällt der Code auf `_pick_character()` zurück und würfelt ungewollt neu.
- **Compact-Threshold wird auf max. 70 geklemmt.** Sowohl bei Create (`compact_threshold_pct=70`) als auch bei jedem `state`-Aufruf eines existierenden Buddys (`>70 → 70`). Buddy soll früher kompaktieren als ein normaler Agent, weil die Lifetime-Session theoretisch unbegrenzt wächst. Achtung: Selbst wenn ein User in den Settings 95 einstellt, würde der nächste `/state`-Aufruf das auf 70 zurücksetzen → die Compaction-Settings-UI ist teilweise wirkungslos für Werte >70 (siehe Offene Enden).
- **Slash-Commands persistieren über `log-cmd`, nicht über den Runner.** Da sie lokal im Frontend laufen, würden sie nach `reload()` verschwinden. `log-cmd` schreibt sie als echte DB-Messages mit `metadata.source = "slash_command"`. `_BuddyThread` rendert diese im **Mono-Mode** (kein Markdown, keine Reload-Action, kein Footer) — damit Command-Output wie Terminal-Output aussieht und nicht versehentlich als LLM-Antwort wiederholbar ist.
- **Session-wechselnde Commands persistieren NICHT.** `/clear`/`/character` returnen `newSessionId`; `handleSend` macht dann `return` vor dem `logCmd` — sinnvoll, weil die alten `localMsgs` an die alte Session gebunden sind und die neue Session leer sein soll.
- **`context` (Settings-Tab) wird in den System-Prompt gebacken, nicht ins Memory-Tool.** Der freie Kontext-Text landet via `_build_soul` als `## Kontext über {username}`-Block direkt im System-Prompt → ist in jedem Turn präsent (kein Recall nötig). Persistiert wird er im Memory-Key `_pref_context` (nur als Quelle für den nächsten Rebuild, nicht als abrufbarer Memory-Eintrag im Recall-Sinn).
- **Emote-Hint ist Frontend-gekoppelt.** `EMOTE_NAMES` in `_emote_hint.py` muss manuell mit `frontend/src/features/chat/hydraEmotes.ts` synchron gehalten werden (im Code-Kommentar explizit notiert). Driftet die Liste, schreibt der Buddy `:hydra-X:` für ein X, das das Frontend nicht rendern kann.

### Was bricht, wenn man X anfasst
- **`is_buddy`-Default ändern:** `_config_utils.py:46` setzt `False`. Würde der Default `True`, würden ALLE Agents zu Buddys (Emote-Hint überall, `_find_buddy_for` nähme zufällige).
- **`agent_config.create`-Signatur (temperature/max_tokens/thinking_budget sind in `__init__.py` positional-by-keyword übergeben):** Änderung der Pflicht-Args bricht Buddy-Create.
- **Charakter-String-Format:** Jede Änderung an `"<Figur> (aus <Universum>)"` bricht den Reparse in `patch_config`.
- **`getSoul`-Endpoint ist `require_admin`:** `/soul`-Slash-Command schlägt für Nicht-Admin-User mit 403 fehl. `soulCmd` fängt das ab und zeigt "Soul nicht abrufbar". Buddy gehört zwar dem User, aber Soul-Inspektion bleibt admin-gated.
- **Landing-Switcher:** `App.tsx:63` macht Buddy zur Default-Landing wenn `getLanding() !== "dashboard"`. Ändert man `getLanding`, ändert sich der Start-Screen.

---

## Datenmodell

### Agent-Config (JSON pro Agent, normalisiert via `_config_utils.normalize`)
Buddy ist ein Eintrag in der Agent-Config mit diesen relevanten Feldern:
| Feld | Wert beim Buddy | Quelle |
|---|---|---|
| `agent_type` | `"master"` | `__init__.py:115` |
| `name` | `"<username>'s Buddy"` (editierbar) | `__init__.py:116` / Settings `name` |
| `owner` / `created_by` | `username` | `__init__.py:118-119` |
| `llm_model` | Default-Modell oder erstes Provider-Modell | `__init__.py:106-110` |
| `system_prompt` | Soul (via `_build_soul`) | `__init__.py:121` |
| `temperature` | `1.0` | `__init__.py:123` |
| `max_tokens` | `16000` | `__init__.py:124` |
| `thinking_budget` | `0` | `__init__.py:125` |
| `is_buddy` | `True` | `__init__.py:126` |
| `compact_threshold_pct` | `70` (geklemmt) | `__init__.py:126`, default-norm `_config_utils` |
| `compact_model` | "" = Hauptmodell (Settings) | Settings |
| `tool_result_max_chars` | 0 = kein Limit (Settings) | Settings |
| `tools` | Liste aktiver Tools (Settings) | Settings |
| `description` | "Persönlicher Buddy — auto-erstellt …" | `__init__.py:120` |

### Memory-Keys (Datei `<agents_dir>/<agent_id>/memory.json`)
| Key | Inhalt | Geschrieben von |
|---|---|---|
| `character` | `"<Figur> (aus <Universum>)"` | Create, `reroll_character`, `patch_config` |
| `_pref_language` | `de` / `en` / `auto` | `patch_config` (Settings) |
| `_pref_tone` | `locker` / `professionell` / `knapp` | `patch_config` (Settings) |
| `_pref_context` | freier Kontext-Text (≤8000) | `patch_config` (Settings) |
| `session_<YYYY-MM-DD>` (ggf. `_HHMMSS`) | Markdown-Snapshot der Session | `/remember` (Snapshot-Modus) |
| `<slug(name)>` | benannte Notiz / Snapshot | `/remember` mit name |
| `note_<unix>` | freie Notiz (nur direkte API) | `/remember` mit text |

### Sessions-Tabelle (`sessions`)
Buddy-Sessions sind normale Rows: `agent_id` = Buddy-Agent, `user_id` = username, `title` = `"<username>'s Buddy"`, `project_id` = `None`. "Aktiv" = neueste nach `created_at`.

### Messages-Tabelle (`messages`)
Slash-Command-Bubbles: `role` user/assistant, `content` text-Block, `metadata.source = "slash_command"`.

### API-Request-Schemas (Pydantic, `buddy.py`)
- `RememberBody{ text?: str≤4000, name?: str≤80 }`
- `ModelBody{ model: str 1–200 }`
- `LogCmdBody{ user_text: str 1–2000, assistant_text: str 1–8000 }`
- `BuddyConfigPatch{ name?≤120, tools?: str[], compact_threshold_pct?: 20–100, compact_model?≤200, tool_result_max_chars?: ≥0, language?: ^(de|en|auto)$, tone?: ^(locker|professionell|knapp)$, context?≤8000 }`

### Response-Shapes
- `BuddyState{ agent_id, session_id, agent_name, model, created }`
- `get_config`-Response = `BuddyConfig` (name, model, character, tools, all_tools, compact_threshold_pct, compact_model, tool_result_max_chars, language, tone, context)
- `patch_config`-Response = `{ ok, new_session_id }`

### Env-Vars / Settings-Singleton-Keys
- Kein eigenes Env-Var für Buddy. Indirekt: `settings.agents_dir` (Memory-Datei-Pfad), `load_config()` (Default-Modell aus LLM-Config).

---

## Offene Enden

- **Tote/inkonsistente Konstante `BUDDY_SOUL`** (`__init__.py:62`): wird mit Platzhalter-Username `"PLACEHOLDER"` gebaut und exportiert, aber im aktiven Pfad nirgends genutzt (nur "Backwards-compat"). Modul-Import würfelt dabei jedes Mal einen Charakter (`_init_universe/_init_char`), der sofort weggeworfen wird. Kandidat zum Entfernen.
- **Compact-Threshold-Klemme widerspricht der Settings-UI:** `_BuddySettingsCompaction` erlaubt 20–95% und `BuddyConfigPatch` erlaubt sogar bis 100. Aber `get_or_create_buddy` setzt bei jedem `/state`-Aufruf jeden Wert >70 wieder auf 70 zurück. Ein in den Settings gespeicherter Wert von z.B. 90 überlebt nur bis zum nächsten Page-Load. Drift zwischen UI-Versprechen und Backend-Verhalten.
- **`/remember` mit freiem Text ist UI-tot:** Backend unterstützt 3 Modi (inkl. freie Notiz `text`), aber das Frontend (`commands.ts:128-131`) ruft `/remember` nur mit `{name}` oder `{}` auf. Der `text`-Pfad (`note_<unix>`) ist nur via direktem API-Call erreichbar.
- **`/soul` ist faktisch admin-only** (`getSoul`-Endpoint `require_admin`). Für normale User schlägt der Befehl fehl und zeigt "Soul nicht abrufbar". Inkonsistenz: alle anderen Buddy-Commands sind user-zugänglich.
- **`reroll_character` ignoriert gespeicherte Prefs:** `commands.py:105` ruft `_build_soul(username, universe, character)` ohne `language`/`tone`/`context`. Würfelt der User einen neuen Charakter via `/character` oder dem Reroll-Button, fällt der Soul auf **Default-Sprache `de`, Default-Ton `locker`, leeren Kontext** zurück — die in den Settings gesetzten Prefs gehen verloren, bis man die Settings erneut speichert. `patch_config` macht es korrekt (liest alle Prefs), `reroll_character` nicht. Klarer Bug/Drift.
- **i18n-Reste:** `de/buddy.json` enthält noch `placeholder`/`coming_soon` ("Hier wohnt bald dein persönlicher Chat-Kumpel … Tamagotchi-Bee, Online-Radio …") und `empty_hint` — Überbleibsel aus der Platzhalter-Phase, die in den aktiven Komponenten nicht mehr verwendet werden (Empty-State ist hardcoded "Frische Tentakel, frischer Chat" in `_BuddyThread`). `settings.tab_extensions` ist in der Locale, aber es gibt keinen Extensions-Tab in `BuddySettingsPage` (nur identity/context/tools/compaction).
- **Hardcoded deutsche Strings statt i18n:** `_BuddySettingsContext`, `_BuddySettingsTools`, `_BuddySettingsCompaction`, `_BuddyExtensionsPanel`, `HealthBuddyBox` und der Empty-State in `_BuddyThread` nutzen feste deutsche Texte statt `t()` — die i18n-Abdeckung des Subsystems ist lückenhaft.
- **Kein Race-Schutz beim Auto-Create:** `get_or_create_buddy` ist nicht atomar. Zwei parallele erste `/state`-Requests könnten zwei Buddy-Agents anlegen. Keine DB-Constraint verhindert das.
- **Emote-Namensliste manuell synchron zu halten** (`_emote_hint.py` ↔ `hydraEmotes.ts`): klassische Drift-Falle, im Code-Kommentar als bewusster Kompromiss markiert ("selten — Emotes ändern sich kaum").
- **`_pref_*`-Memory-Keys verschmutzen den Memory-Namespace:** Sie liegen in derselben `memory.json` wie echte Recall-Memories und `/remember`-Notizen. Beginnen mit `_` (vermutlich als Konvention zum Ausblenden), aber ob der Recall-/Memory-Browser sie filtert, ist hier nicht verifiziert — potenzielle Vermischung von "Prefs" und "abrufbarem Wissen".
- **`/agent` zeigt gekürzte IDs** (`.slice(0,8)`) — rein kosmetisch, kein Bug, aber für Debugging unvollständig.
