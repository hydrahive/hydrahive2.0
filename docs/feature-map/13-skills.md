# Skills

Wiederverwendbare Verhaltensmuster (Instruction-Templates) als Markdown-Dateien mit
YAML-Frontmatter. Drei Scopes (system / user / agent), Filesystem-basierte CRUD,
gemergte Sicht pro Agent, Injektion ins System-Prompt als Tabelle, plus zwei LLM-Tools
(`list_skills`, `load_skill`) zum Abruf zur Laufzeit. Optionale externe Quellen
(`sources`) mit Credential-Profil-Verknüpfung für `fetch_url`.

---

## WAS

Einzelpunkte — jede Fähigkeit / Datei / Funktion / Endpoint / Tool / Config-Flag / UI-Komponente.

### Backend-Module (Python)

- **`skills/__init__.py`** — Public-API-Fassade des Subsystems. Re-exportiert
  `delete_skill`, `get_skill`, `list_for_agent`, `save_skill` aus dem Loader und
  `Skill`, `SkillScope` aus den Models. Enthält den maßgeblichen Docstring mit der
  Format-Spezifikation einer Skill-Datei.
- **`skills/models.py`** — Datenmodelle + Parser + Serializer.
  - `SkillScope` — `Literal["system", "user", "agent"]`.
  - `SkillSource` (dataclass) — externe Quelle (`url`, `auth`, `description`).
  - `Skill` (dataclass) — `name`, `description`, `when_to_use`, `body`, `scope`,
    `owner`, `tools_required: list[str]`, `sources: list[SkillSource]`.
  - `is_valid_name(name)` — Validierung gegen `NAME_RE`.
  - `_parse_tools(raw)` — akzeptiert Liste ODER Komma-String (Claude-Code-Format
    `"Read, Grep, Bash"`).
  - `_parse_sources(raw)` — akzeptiert dicts oder bloße URL-Strings; filtert leere URLs.
  - `parse(text, *, scope, owner, fallback_name)` — Frontmatter-Split + YAML-Load,
    Fallback bei fehlendem/kaputtem Frontmatter.
  - `serialize(skill)` — rendert Skill zurück zu Markdown mit YAML-Frontmatter.
- **`skills/loader.py`** — Filesystem-CRUD.
  - `install_system_defaults()` — kopiert mitgelieferte Default-Skills nach
    `$HH_DATA_DIR/skills/system/`, überschreibt nie existierende.
  - `_collect_skill_files(d)` — sammelt Skill-Dateien aus 3 Layouts (flach,
    `name/SKILL.md`, `category/name/SKILL.md`), dedupliziert.
  - `_list_dir(d, scope, owner)` — parst alle Skills eines Verzeichnisses.
  - `list_for_agent(agent_id, owner, *, disabled)` — merged system+user+agent,
    Kollision: agent > user > system; blendet `disabled`-Namen aus; sortiert.
  - `get_skill(scope, owner, name)` — Einzel-Skill, `None` bei invalid/fehlt.
  - `save_skill(skill)` — atomarer Write (`.tmp` + `replace`); validiert Namen.
  - `delete_skill(scope, owner, name)` — `unlink`; `False` wenn nicht existent.
- **`skills/_paths.py`** — Pfad-Auflösung.
  - `system_dir()` → `$HH_DATA_DIR/skills/system`.
  - `user_dir(username)` → `$HH_DATA_DIR/users/<username>/skills`.
  - `agent_dir(agent_id)` → `$HH_DATA_DIR/agents/<agent_id>/skills`.
  - `dir_for(scope, owner)` — Dispatch nach Scope (raises `ValueError` bei unbekannt).
  - `file_for(scope, owner, name)` → `dir_for(...)/<name>.md`.

### System-Default-Skills (ausgeliefert, 21 Stück)

In `skills/system_defaults/*.md`. Jeder hat `name`, `description`, `when_to_use`,
`tools_required`. Beim ersten Start nach `$HH_DATA_DIR/skills/system/` kopiert.

- **`brainstorming`** (tools: `file_write, shell_exec`) — Design-first: erst
  vollständige Spezifikation, dann Code.
- **`code-review`** (`file_read, shell_exec`) — Strukturierter Code-Review mit
  fokussierter Reihenfolge.
- **`debugging`** (`shell_exec, file_read`) — Strukturierter Bug-Hunt (Ist-Zustand →
  Hypothesen).
- **`dispatching-parallel-agents`** (`shell_exec`) — Sub-Agenten für unabhängige
  Teilprobleme parallel.
- **`docs`** (`read_file, write_file, grep, glob`) — Doku/API-Docs/README/Kommentare.
- **`finishing-development-branch`** (`shell_exec`) — Abschluss eines Branches, Tests
  zuerst.
- **`generate-music`** (`generate_music`) — Musik mit Lyria 3 erzeugen.
- **`generate-speech`** (`generate_speech`) — Text → TTS (Stimmen, Sprachen, Fehler).
- **`git-workflow`** (`shell_exec`) — Saubere Git-Commits + Push-Pattern.
- **`hh-review`** (`read_file, grep, glob, bash`) — HydraHive2-spezifischer Code-Review
  gegen CLAUDE.md-Regeln (Dateigröße, Co-location, Architektur, kein `print()`,
  Settings-Singleton, keine Zirkular-Imports).
- **`medical-akte`** (`fetch_url`; zusätzlich nicht-parsierter `metadata: category: health`)
  — strukturierte Patientenakte (ePA-light) über die REST-API befüllen.
- **`medical-research`** (`fetch_url`) — Recherche über offene APIs (PubMed etc.).
- **`performance-profile`** (`shell_exec, file_read`) — Token-Verbrauch + Cache-Hit-Rate
  analysieren.
- **`project-management`** (`shell_exec`) — GitHub Issues/PRs verwalten.
- **`refactor`** (`read_file, write_file, grep, glob`) — Refactoring (SOLID etc.).
- **`security-audit`** (`file_read, shell_exec`) — Security-Check für Endpoints/Tools/Auth.
- **`skill-catalog`** (`list_skills`) — `list_skills` aufrufen, Markdown-Tabelle aller
  Skills ausgeben, User nach Wahl fragen, mit `load_skill` laden.
- **`test`** (`read_file, write_file, bash, grep`) — Unit/Integrations-Tests + Test-Daten.
- **`using-superpowers`** (`list_skills, load_skill`) — erklärt das Skill-System und wann
  Skills genutzt werden müssen.
- **`verification-before-completion`** (`shell_exec, file_read`) — 5-Schritt-Gate vor
  „fertig".
- **`writing-plans`** (`file_write`) — Strukturierte Pläne vor dem Coden (atomare
  TDD-Tasks).

### API-Endpoints (`api/routes/skills.py`, Prefix `/api/skills`, Tag `skills`)

- **`GET /api/skills`** (`list_skills_endpoint`) — Query `agent_id?`, `scope=system|user|agent|all`
  (Default `all`). Mit `agent_id`: gemergte Liste für den Agent (system+user+agent,
  abzgl. `disabled_skills`). Ohne: scope-gefiltert (system + eigene user-Skills).
  Auth via `require_auth`.
- **`GET /api/skills/{scope}/{name}`** (`get_skill_endpoint`) — Query `owner?`. Einzel-Skill.
  404 `skill_not_found`, 403 `skill_no_access`, 400 `skill_owner_required`.
- **`POST /api/skills/{scope}`** (`create_or_update`) — Status 201. Body = `SkillBody`.
  Query `owner?`. Create-or-Update (gleicher Name überschreibt). system → admin-only;
  user → owner==username (admin kann fremd); agent → Access-Check.
  Fehler: 400 `skill_name_invalid`, 403 `admin_only`, 400 `skill_owner_required`,
  400 `skill_save_failed`.
- **`DELETE /api/skills/{scope}/{name}`** (`delete_skill_endpoint`) — Status 204. Query
  `owner?`. Gleiche Scope-/Auth-Logik wie POST. 404 `skill_not_found`.

### Schemas / Helper (`api/routes/_skill_route_helpers.py`)

- `SkillSourceBody` (Pydantic) — `url`, `auth=""`, `description=""`.
- `SkillBody` (Pydantic) — `name` (1–50), `description`, `when_to_use`,
  `tools_required: list[str]`, `sources: list[SkillSourceBody]`, `body`.
- `serialize_skill(s)` — Skill-dataclass → dict (inkl. `scope`, `owner`).
- `check_agent_access(agent_id, username, role)` — lädt Agent-Config, prüft
  Owner/Admin; raises 404 `agent_not_found` / 403 `agent_no_access`.

### LLM-Tools (Anthropic-Format, Kategorie `agents`)

- **`list_skills`** (`tools/list_skills.py`) — kein Argument. Liefert `{skills: [...],
  count}` mit `name`, `description`, `when_to_use`, `scope`, `tools_required` je Skill
  (gemergt + `disabled_skills` gefiltert).
- **`load_skill`** (`tools/load_skill.py`) — Argument `name` (required). Liefert vollen
  Skill: `name`, `description`, `when_to_use`, `tools_required`, `sources` (Liste mit
  `url`/`auth`/`description`), `body`, `scope`. Fehlt der Skill: Fail mit Liste der
  verfügbaren Namen.

### System-Prompt-Injektion (`runner/system_prompt.py`)

- `_stable_section(...)` — hängt bei vorhandenen Skills eine `## Skills`-Markdown-Tabelle
  an den stabilen (cache-fähigen) System-Prompt: pro Skill `| `name` | when_to_use oder
  description |`, plus Aufforderung „Lade einen Skill mit `load_skill(name)` **bevor** du
  mit einer Aufgabe beginnst. Wenn auch nur 1% Chance besteht dass ein Skill passt — lade
  ihn zuerst."

### Frontend (React/TS, `features/skills/`)

- **`types.ts`** — `SkillScope`, `SkillSource`, `Skill`, `SkillSavePayload`.
- **`api.ts`** — `skillsApi` mit `list`, `get`, `save`, `remove` (REST-Wrapper).
- **`SkillsPage.tsx`** — Hauptseite (Route `/skills`). Zwei Sektionen: „Your skills"
  (scope=user) und „System skills" (scope=system). `Section`-Subkomponente rendert
  Skill-Cards. Neu-Button öffnet `SkillEditor` (defaultScope user).
- **`SkillEditor.tsx`** — Modal-Editor (Name/Description/when_to_use/tools_required/
  sources/body). Name immutable nach Erstellung. Client-Validierung via `NAME_RE`.
  Save/Delete/Cancel. Delete nur wenn scope≠system und `onDeleted` gesetzt.
- **`_skillHelpers.tsx`** — `Field`-Layout-Komponente (Label + optional Hint).
- **`_SkillSourcesList.tsx`** — Editor für `sources` (url/description/auth pro Zeile,
  Add/Remove).
- **`features/agents/_SkillsTab.tsx`** — Agent-Detail-Tab „Skills": listet gemergte
  Skills des Agents, On/Off-Checkbox pro Skill (schreibt in `draft.disabled_skills`),
  Edit-Button (öffnet `SkillEditor` mit defaultScope=agent, ownerForSave=agent.id),
  Neu-Button.

### Config-Flags / Felder

- **`disabled_skills: list[str]`** — pro Agent-Config; Liste deaktivierter Skill-Namen.
  Default `[]` via `normalize` (`agents/_config_utils.py:44`).
- **Default-Toolsets** (`agents/_defaults.py`) — `list_skills` + `load_skill` sind in
  ALLEN drei Agent-Typen (`master`, `project`, `specialist`) standardmäßig enthalten.

---

## WIE — Ablauf & Datenfluss

### Boot: Default-Skills installieren
`lifespan()` (`api/lifespan.py:92-93`) → `install_system_defaults()` →
`system_dir()` mkdir → für jede `system_defaults/*.md`: kopiere nach
`$HH_DATA_DIR/skills/system/<name>.md` **nur wenn dort noch nicht vorhanden**
(`shutil.copy2`, idempotent, Admin-Edits bleiben erhalten).

### Skill anlegen/bearbeiten (UI → DB)
1. User klickt „New skill" in `SkillsPage` / `_SkillsTab` → `SkillEditor` öffnet.
2. Eingabe; `save()` validiert Namen client-seitig (`NAME_RE`), splittet
   `tools_required` per Komma, filtert leere Sources.
3. `skillsApi.save(scope, payload, owner?)` → `POST /api/skills/{scope}?owner=...`.
4. Route `create_or_update`: `require_auth` → `is_valid_name` → Scope-/Owner-Auflösung
   + Auth (admin für system, owner-match für user, `check_agent_access` für agent) →
   baut `Skill`-dataclass → `save_skill`.
5. `save_skill` → `is_valid_name` → `dir_for(...)` mkdir → `serialize(skill)` (YAML
   Frontmatter + Body) → atomarer `.tmp`-Write + `replace`.
6. UI `onSaved` → `reload()` → erneutes `GET /api/skills`.

### Skill listen für einen Agent (gemergte Sicht)
`GET /api/skills?agent_id=X` → `_check_agent_access` → `agent["disabled_skills"]` →
`list_for_agent(agent_id, owner, disabled=...)`:
1. `_list_dir(system_dir(), "system", "system")` → bag[name]=skill
2. `_list_dir(user_dir(owner), "user", owner)` → überschreibt bei Namensgleichheit
3. `_list_dir(agent_dir(agent_id), "agent", agent_id)` → überschreibt erneut
4. Filter `disabled`-Namen, sortiert nach Name. → `serialize_skill` je Skill.

`_list_dir` ruft `_collect_skill_files` (3 Layouts: `*.md`, `*/SKILL.md`,
`*/*/SKILL.md`, case-Varianten `skill.md`) → für jede Datei `read_text` →
`parse(text, scope, owner, fallback_name)` → falls `name` leer, auf `fallback_name`
setzen.

### Skill ins LLM bringen (Runtime)
1. Runner-Start (`runner/runner.py:119`): `agent_skills = load_agent_skills(agent["id"],
   agent["owner"], disabled=agent.get("disabled_skills") or [])` (= `list_for_agent`).
2. `compose_system_prompts(..., skills=agent_skills, ...)` (`runner.py:153`) →
   `_stable_section` hängt die Skill-Tabelle an den **stabilen** (cache-fähigen)
   System-Prompt. Tabelle zeigt nur `name` + `when_to_use||description`, NICHT den Body.
3. Agent ruft `list_skills` (sieht Metadaten) bzw. `load_skill(name)` (bekommt Body +
   sources als Tool-Result) — die Tools laden bei jedem Aufruf frisch via
   `list_for_agent` (Agent-Config + Owner-Auflösung über `ctx.agent_id`/`ctx.user_id`).

### Source-Auth (geplante Verdrahtung)
`load_skill` liefert `sources` als strukturiertes Feld zurück. Der Agent soll die URLs
selbst per `fetch_url` abrufen; `fetch_url` (`tools/fetch_url.py`) macht
`match_credential(user_id, url, prefer_name=auth_name)` → injiziert Token transparent in
HTTP-Header (Token kommt NIE in den LLM-Kontext). Das `auth`-Feld einer Source ist der
Credential-Profilname. **Achtung:** die Verknüpfung Source→fetch_url ist NICHT
automatisiert (siehe WARUM/Offene Enden).

### Per-Agent An/Aus (UI → ?)
`_SkillsTab.toggle(name)` mutiert `draft.disabled_skills` und ruft `onChange`. Beim
Speichern der Agent-Form: `agentsApi.update(agent.id, rest)` → `PATCH /api/agents/{id}`
→ `update_agent` → `req.model_dump(exclude_unset=True)` → `agent_config.update(...)`.
**Dabei geht `disabled_skills` verloren** (siehe WARUM — Drift).

---

## WO — Datei:Zeile

### Models & Parsing
- `core/src/hydrahive/skills/models.py:12` — `SkillScope`
- `core/src/hydrahive/skills/models.py:14` — `NAME_RE = ^[a-z0-9][a-z0-9_-]{0,49}$`
- `core/src/hydrahive/skills/models.py:16` — `_FRONTMATTER_RE`
- `core/src/hydrahive/skills/models.py:19-27` — `SkillSource` dataclass
- `core/src/hydrahive/skills/models.py:30-39` — `Skill` dataclass
- `core/src/hydrahive/skills/models.py:42-43` — `is_valid_name`
- `core/src/hydrahive/skills/models.py:46-52` — `_parse_tools` (Liste oder Komma-String)
- `core/src/hydrahive/skills/models.py:55-68` — `_parse_sources`
- `core/src/hydrahive/skills/models.py:71-94` — `parse`
- `core/src/hydrahive/skills/models.py:89` — `tools_required` liest `tools_required`
  ODER `allowed-tools` (Claude-Code-Kompat)
- `core/src/hydrahive/skills/models.py:97-113` — `serialize`

### Loader
- `core/src/hydrahive/skills/loader.py:14` — `_DEFAULTS_SRC = .../system_defaults`
- `core/src/hydrahive/skills/loader.py:17-29` — `install_system_defaults`
- `core/src/hydrahive/skills/loader.py:32-58` — `_collect_skill_files` (3 Layouts)
- `core/src/hydrahive/skills/loader.py:54` — Glob-Patterns inkl. `SKILL.md`/`skill.md`
- `core/src/hydrahive/skills/loader.py:61-75` — `_list_dir`
- `core/src/hydrahive/skills/loader.py:78-89` — `list_for_agent` (Merge + disabled)
- `core/src/hydrahive/skills/loader.py:92-98` — `get_skill`
- `core/src/hydrahive/skills/loader.py:101-110` — `save_skill` (atomarer Write)
- `core/src/hydrahive/skills/loader.py:113-118` — `delete_skill`

### Pfade
- `core/src/hydrahive/skills/_paths.py:9-10` — `system_dir`
- `core/src/hydrahive/skills/_paths.py:13-14` — `user_dir`
- `core/src/hydrahive/skills/_paths.py:17-18` — `agent_dir`
- `core/src/hydrahive/skills/_paths.py:21-28` — `dir_for`
- `core/src/hydrahive/skills/_paths.py:31-32` — `file_for`

### Public-API
- `core/src/hydrahive/skills/__init__.py:24-30` — Re-Exports
- `core/src/hydrahive/skills/__init__.py:32` — `__all__`

### Routes
- `core/src/hydrahive/api/routes/skills.py:27` — Router (`/api/skills`)
- `core/src/hydrahive/api/routes/skills.py:30-48` — `list_skills_endpoint`
- `core/src/hydrahive/api/routes/skills.py:42` — `disabled = agent["disabled_skills"]`
- `core/src/hydrahive/api/routes/skills.py:51-72` — `get_skill_endpoint`
- `core/src/hydrahive/api/routes/skills.py:75-105` — `create_or_update`
- `core/src/hydrahive/api/routes/skills.py:108-127` — `delete_skill_endpoint`
- `core/src/hydrahive/api/routes/_skill_route_helpers.py:12-15` — `SkillSourceBody`
- `core/src/hydrahive/api/routes/_skill_route_helpers.py:18-24` — `SkillBody`
- `core/src/hydrahive/api/routes/_skill_route_helpers.py:27-33` — `serialize_skill`
- `core/src/hydrahive/api/routes/_skill_route_helpers.py:36-42` — `check_agent_access`
- `core/src/hydrahive/api/main.py:51` — Import `skills_router`
- `core/src/hydrahive/api/main.py:125` — `app.include_router(skills_router)`

### Tools
- `core/src/hydrahive/tools/list_skills.py:15-33` — `_execute`
- `core/src/hydrahive/tools/list_skills.py:36-42` — `TOOL` (category `agents`)
- `core/src/hydrahive/tools/load_skill.py:21-46` — `_execute`
- `core/src/hydrahive/tools/load_skill.py:42-43` — `sources` ins Tool-Result
- `core/src/hydrahive/tools/load_skill.py:49-55` — `TOOL`
- `core/src/hydrahive/tools/__init__.py:29-30,67-68` — Registry-Eintrag

### Runner / System-Prompt
- `core/src/hydrahive/runner/runner.py:36` — `from ...loader import list_for_agent as load_agent_skills`
- `core/src/hydrahive/runner/runner.py:119` — `agent_skills = load_agent_skills(...)`
- `core/src/hydrahive/runner/runner.py:153-158` — `compose_system_prompts(..., skills=agent_skills)`
- `core/src/hydrahive/runner/system_prompt.py:54-79` — `_stable_section` (Skill-Tabelle)
- `core/src/hydrahive/runner/system_prompt.py:66-78` — Tabelle + „1%-Chance"-Aufforderung

### Boot
- `core/src/hydrahive/api/lifespan.py:92-93` — `install_system_defaults()`

### Defaults & Agent-Config
- `core/src/hydrahive/agents/_defaults.py:12,21,24` — `list_skills`/`load_skill` in
  `master`/`project`/`specialist`
- `core/src/hydrahive/agents/_config_utils.py:44` — `cfg.setdefault("disabled_skills", [])`
- `core/src/hydrahive/agents/config.py:78-119` — `update` (kein `disabled_skills`-Whitelist)
- `core/src/hydrahive/api/routes/_agent_schemas.py:35-56` — `AgentUpdate` (KEIN
  `disabled_skills`-Feld)
- `core/src/hydrahive/api/routes/agents.py:110-123` — `update_agent` (`model_dump(exclude_unset)`)

### Credentials-Verknüpfung
- `core/src/hydrahive/credentials/__init__.py:6-8` — Docstring: „Skills referenzieren
  Credentials per Profile-Name `sources: - {url, auth: <profile_name>}`"
- `core/src/hydrahive/tools/fetch_url.py:69-75` — `_select_cred` / `match_credential`

### Frontend
- `frontend/src/features/skills/types.ts:1-27` — Typen
- `frontend/src/features/skills/api.ts:4-25` — `skillsApi`
- `frontend/src/features/skills/SkillsPage.tsx:11-70` — `SkillsPage`
- `frontend/src/features/skills/SkillsPage.tsx:27-28` — Split user/system
- `frontend/src/features/skills/SkillsPage.tsx:72-101` — `Section`
- `frontend/src/features/skills/SkillEditor.tsx:20` — `NAME_RE` (Client)
- `frontend/src/features/skills/SkillEditor.tsx:22-66` — Editor-Logik (save/remove)
- `frontend/src/features/skills/_skillHelpers.tsx:1-11` — `Field`
- `frontend/src/features/skills/_SkillSourcesList.tsx:10-45` — Sources-Editor
- `frontend/src/features/agents/_SkillsTab.tsx:15-102` — `SkillsTab`
- `frontend/src/features/agents/_SkillsTab.tsx:30-36` — `disabled`-Set + `toggle`
- `frontend/src/features/agents/types.ts:30` — `disabled_skills?: string[]`
- `frontend/src/features/agents/AgentForm.tsx:97` — `<SkillsTab .../>` Einhängung
- `frontend/src/App.tsx:86` — Route `skills` → `SkillsPage`
- `frontend/src/shared/colors.ts:26` — `"/skills": "orange"` (Akzentfarbe)
- `frontend/src/i18n/locales/en/skills.json` + `de/skills.json` — i18n-Namespace `skills`

### System-Default-Skills
- `core/src/hydrahive/skills/system_defaults/*.md` — 21 Dateien (~1519 Zeilen gesamt)

---

## WARUM — nicht-offensichtliche Verdrahtung, Invarianten, Gotchas

### Architektur-Entscheidungen
- **Filesystem statt DB:** Skills sind Markdown-Dateien — kein DB-Schema, kein Migration.
  Damit lassen sich Skills wie Code/Doku versionieren, manuell editieren, und der Installer
  liefert Defaults als pure Dateien aus. CRUD ist explizit „idempotent, kein Lock" (Loader-
  Docstring) — gleichzeitige Saves an dieselbe Datei gelten als unwahrscheinlich (User-Editor).
- **Atomarer Write:** `save_skill` schreibt `.md.tmp` und `replace`t — verhindert
  halb-geschriebene Dateien bei Crash. Gleiche Disziplin wie Agent-Configs.
- **Stable-vs-Volatile-Prompt:** Die Skill-Tabelle hängt im STABLEN Block — sie ist pro
  Agent/Session unveränderlich und damit cache-fähig (Anthropic prüft den ganzen
  System-Block byteweise). Würde man Skills in den volatilen Block legen, bräche der Cache
  ständig. Invariante: Skills ändern sich innerhalb einer Session nicht (sie werden EINMAL
  bei Runner-Start via `load_agent_skills` geladen — `runner.py:119`).

### Merge-Invariante (Scope-Präzedenz)
`list_for_agent` füllt ein `bag: dict[name → Skill]` in der Reihenfolge system → user →
agent. Spätere Scopes überschreiben gleichnamige → **agent > user > system**. Wer einen
System-Skill „überschreiben" will, legt einen gleichnamigen user-/agent-Skill an. Das ist
gewollt (Default überschreibbar ohne den System-Skill zu löschen). Wer einen Skill
KOMPLETT ausblenden will, nutzt `disabled_skills` (Filter NACH dem Merge).

### Owner-Auflösung in den Tools
`list_skills`/`load_skill` lösen den Owner über `agent.get("owner") or ctx.user_id` auf
(`list_skills.py:21`, `load_skill.py:30`). Das ist wichtig: User-Skills hängen am
Owner-Username, nicht am `ctx.user_id`. Wenn ein Agent keinen Owner hat (sollte nicht
vorkommen), fällt es auf den laufenden User zurück.

### Tools sind immer da, Body nur on demand
`list_skills`+`load_skill` sind in allen Agent-Typen Default (`_defaults.py`). Die
Skill-Tabelle im Prompt zeigt nur Metadaten — der (potenziell lange) Body wird erst per
`load_skill` geladen. Das hält den gecachten System-Prompt klein. Der „1%-Chance"-Hinweis
pusht den Agenten aktiv zum Laden.

### Format-Toleranz (Claude-Code-Kompat)
- `_parse_tools` akzeptiert sowohl Listen als auch Komma-Strings (`"Read, Grep, Bash"`).
- `parse` liest `tools_required` ODER `allowed-tools` (Claude-Code-Frontmatter-Key).
- `_collect_skill_files` versteht 3 Verzeichnis-Layouts inkl. `name/SKILL.md` (benithors/
  skills-Style) und `category/name/SKILL.md` (Orchestra-Research-Style).
Das erlaubt, fremde Skill-Packs (Claude-Code, Superpowers) weitgehend unverändert
einzukippen — der `fallback_name` kommt aus dem Eltern-Verzeichnis bzw. Datei-Stem.

### Was bricht, wenn man X anfasst
- **`NAME_RE` ändern** (models.py:14): muss synchron mit der Client-Regex
  (`SkillEditor.tsx:20`) bleiben — sonst akzeptiert das Frontend Namen, die das Backend
  ablehnt (oder umgekehrt). Dateiname ist `<name>.md`, also bestimmt der Name den Pfad.
- **`_paths.py` umbauen**: `system_dir`/`user_dir`/`agent_dir` definieren das Layout, das
  `install_system_defaults` und alle CRUD-Funktionen voraussetzen. Änderung bricht das
  Auffinden bestehender Skills auf der Platte.
- **Skill-Body in den Prompt aufnehmen** (statt nur Tabelle): würde den gecachten
  System-Prompt aufblähen und den Sinn von `load_skill` (lazy load) zerstören.
- **`serialize`/`parse` divergieren lassen**: Round-Trip muss stabil sein — sonst
  verändert ein UI-Save bei jedem Speichern die Datei (oder verliert Felder wie das
  nicht-modellierte `metadata`).

### Sicherheits-/Auth-Logik
- system-Skills: nur Admin schreibt/löscht; alle lesen.
- user-Skills: Owner==username; Admin darf fremd-owner setzen.
- agent-Skills: `check_agent_access` (Owner des Agents oder Admin).
- Credential-Tokens für Sources kommen NIE in den LLM-Kontext — `fetch_url` injiziert sie
  transparent (Credentials-Modul-Docstring + `fetch_url._select_cred`).

---

## Datenmodell

### Dateien (Filesystem, kein DB-Schema)
- **System-Skills:** `$HH_DATA_DIR/skills/system/<name>.md`
- **User-Skills:** `$HH_DATA_DIR/users/<username>/skills/<name>.md`
- **Agent-Skills:** `$HH_DATA_DIR/agents/<agent_id>/skills/<name>.md`
- **Mitgelieferte Defaults (read-only Quelle):**
  `core/src/hydrahive/skills/system_defaults/*.md`

### Skill-Datei-Format (YAML-Frontmatter + Markdown-Body)
```
---
name: code-review            # [a-z0-9][a-z0-9_-]{0,49}, bestimmt Dateinamen
description: ...             # Kurzbeschreibung
when_to_use: ...            # 1 Satz: wann laden (Vorrang in der Prompt-Tabelle)
tools_required: [a, b]      # ODER "a, b"  ODER Key `allowed-tools` (advisory)
sources:                    # optional
  - url: https://...
    auth: <credential_profile_name>   # optional
    description: ...                  # optional
---

Markdown-Body mit Anweisungen…
```
- Frontmatter-Regex: `^---\n(.*?)\n---\n?(.*)$` (DOTALL).
- Ohne valides Frontmatter: ganzer Text wird `body`, `name=fallback_name`.

### `Skill` (dataclass, in-memory)
`name, description, when_to_use, body, scope, owner, tools_required: list[str],
sources: list[SkillSource]`

### `SkillSource` (dataclass)
`url, auth="", description=""`

### API-Response-dict (`serialize_skill`)
`{name, description, when_to_use, tools_required[], sources[{url,auth,description}],
body, scope, owner}`

### Agent-Config-Feld
- `disabled_skills: list[str]` — deaktivierte Skill-Namen (Filter nach dem Merge).
  Default `[]` (`_config_utils.py:44`).

### Env-Vars
- `HH_DATA_DIR` (indirekt via `settings.data_dir`) — Wurzel aller Skill-Pfade.

### Fehler-Codes (coded responses)
`skill_name_invalid`, `skill_not_found`, `skill_no_access`, `skill_owner_required`,
`skill_save_failed`, `admin_only`, `agent_not_found`, `agent_no_access`.

### i18n-Namespace `skills` (en/de)
Keys u.a.: `title`, `subtitle`, `section_user`, `section_system`, `name_invalid`,
`name_immutable`, `when_to_use_hint`, `sources_hint`, `source_auth_hint`,
`agent_tab_subtitle`, `agent_tab_on`, `agent_tab_off`.

---

## Offene Enden — TODOs, tote/halbfertige Teile, Drift, Inkonsistenzen

### 1. `disabled_skills`-Toggle persistiert NICHT (echter Bug / Drift)
`_SkillsTab.toggle` (`_SkillsTab.tsx:32-36`) schreibt `disabled_skills` in den Agent-Draft,
und beim Speichern schickt `AgentForm` (`AgentForm.tsx:54-56`) den ganzen `rest` per
`PATCH /api/agents/{id}`. ABER: `update_agent` macht `req.model_dump(exclude_unset=True)`
auf das `AgentUpdate`-Pydantic-Modell (`agents.py:112`) — und `AgentUpdate`
(`_agent_schemas.py:35-56`) enthält **kein** `disabled_skills`-Feld. Pydantic v2 ignoriert
unbekannte Felder per Default (kein `extra="allow"` gesetzt). → `disabled_skills` wird
stillschweigend aus dem Request gestrippt und erreicht `agent_config.update` nie. Das
Backend (`config.update`, `config.py:78`) würde das Feld zwar durchschreiben (kein
Whitelist), bekommt es aber nicht. **Effekt:** Die On/Off-Checkbox im Agent-Skills-Tab hat
keine bleibende Wirkung. Fix wäre `disabled_skills: list[str] | None = None` in
`AgentUpdate`.

### 2. `sources`→`fetch_url`-Auto-Auth nicht verdrahtet (Doc-Drift)
Der `SkillSource`-Docstring (`models.py:20-24`) behauptet: „Beim `load_skill` werden die
URLs als Hinweis im Body angehängt — der Agent kann sie via `fetch_url()` abrufen, Auth
wird automatisch via Credential-Profile-Match eingehängt." In Wahrheit hängt `load_skill`
**nichts** an den Body an — es liefert `sources` als separates strukturiertes Feld zurück
(`load_skill.py:42-43`). Es gibt keinen Code, der Source-URLs in den Body webt oder
proaktiv `fetch_url` aufruft. Die Auth-Verknüpfung funktioniert nur, wenn der Agent
selbstständig `fetch_url(url, auth=<profil>)` aufruft (oder das Profil per URL-Pattern
matcht). Die „automatische" Einhängung ist also reines `fetch_url`-Verhalten, nicht
Skill-spezifisch.

### 3. `tools_required` ist rein advisory, mit toten Tool-Namen in Defaults
`tools_required` wird nirgends gegen die REGISTRY validiert oder zum Filtern/Aktivieren von
Tools genutzt — es ist nur Anzeige-Metadata. Mehrere Default-Skills deklarieren
Claude-Code-Tool-Namen, die in HydraHive gar nicht existieren: `read_file`, `write_file`,
`grep`, `glob`, `bash` (real: `file_read`, `file_write`, `shell_exec`; kein `grep`/`glob`/
`bash`-Tool). Betrifft u.a. `docs`, `refactor`, `test`, `hh-review`, `skill-catalog`
(letzterer ok: `list_skills` existiert). Harmlos (advisory), aber inkonsistent — wirkt nach
unangepasstem Port aus einem Claude-Code-Skill-Pack.

### 4. Nicht-modelliertes Frontmatter-Feld `metadata`
`medical-akte.md` hat `metadata: category: health` im Frontmatter. `parse` liest weder
`metadata` noch `category` — die Information geht beim Laden verloren. Würde der Skill je
über die UI gespeichert (`serialize`), verschwände `metadata` aus der Datei. Tote
Information.

### 5. POST nutzt Status 201 auch beim Update
`create_or_update` ist „create-or-update" (gleicher Name überschreibt), gibt aber immer
`201 CREATED` zurück — bei reinen Updates semantisch eigentlich `200`. Minor.

### 6. Keine dedizierten Unit-Tests für das Skills-Subsystem
Im Test-Verzeichnis referenzieren nur `test_runner_cache.py`, `test_research_apis.py`,
`test_scratchpad_prompt.py`, `test_recall_weaving.py` das Wort „skills" — keiner testet
gezielt `loader.py`/`models.py`/die Skill-Routes (parse/serialize-Round-Trip, Merge-
Präzedenz, `disabled`-Filter, atomarer Write, 3-Layout-Collection). Lücke gegenüber der
80%-Coverage-Regel.

### 7. Importpfad-Inkonsistenz in der Route
`skills.py:23-24` importiert `_list_dir` und `system_dir`/`user_dir` direkt aus
`loader`/`_paths` (unterstrich-präfigierte „private" Helfer) statt über die `__init__`-
Fassade. Funktioniert, durchbricht aber die Public-API-Kapselung des Pakets.

### 8. `SkillSourceBody` importiert aber im Route-File teils ungenutzt
In `skills.py` wird `SkillSourceBody` importiert (`skills.py:20`), aber nur `SkillSource`
(Model) im Create-Pfad gebraucht — `SkillSourceBody` selbst wird nur via `SkillBody.sources`
indirekt verwendet. Kosmetisch.
