# Feature Map: Agents — Konfiguration & Typen

> **Modul:** `core/src/hydrahive/agents/`  
> **Was:** Agent-Konfiguration, Typen, Bootstrap, Validierung. Agents sind die "Persönlichkeiten".  
> **Warum:** Jeder LLM-Call braucht einen konfigurierten Agent — ohne Config kein Run.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `config.py` | Haupt-Config-Module. `get(agent_id)`, `list()`, `create()`, `update()`, `delete()`. Lädt aus JSON-Dateien. |
| `_config_utils.py` | Hilfsfunktionen für Config-Laden/Speichern |
| `_defaults.py` | Default-Werte (MAX_ITERATIONS, DEFAULT_MAX_TOKENS, etc.) |
| `_paths.py` | Pfad-Funktionen: `ensure_workspace()`, Agent-Verzeichnisse |
| `_prompt.py` | System-Prompt-Zusammenbau aus Agent-Config-Feldern |
| `_validation.py` | Config-Validierung (Pflichtfelder, Typ-Checks) |
| `_workspace_links.py` | Symlinks für Workspace-Shortcuts (`~/projects/<name>`) |
| `bootstrap.py` | Initiale Agents anlegen (beim ersten Start) |
| `external_instances.py` | Externe HH2-Instanz-Agents (Federation) |
| `master/__init__.py` | Master-Agent-Spezifika |
| `project/__init__.py` | Project-Agent-Spezifika |
| `specialist/__init__.py` | Specialist-Agent-Spezifika |

---

## Agenten-Typen

### 1. Master-Agent
- **Einer pro User** (automatisch beim User-Anlegen erstellt)
- **Persona/Buddy**: Hat Namen, Charakter, System-Prompt, Emote-Stil
- **Werkzeugkasten**: Alle Tools verfügbar (shell, file, ask_agent, datamining, ...)
- **Workspace**: `/var/lib/hydrahive2/workspaces/master/<agent-id>/`
- **Sessions**: Direkt im Web-UI ("Buddy"-Tab)
- **is_buddy: true** → bekommt Emote-Hint im System-Prompt

### 2. Project-Agent
- **Einer pro Projekt** (wenn Projekt angelegt wird)
- **Fokussiert** auf Projekt-Aufgaben, hat Zugriff auf Projekt-Workspace
- **Workspace**: `/var/lib/hydrahive2/workspaces/projects/<project-id>/`
- **Wird via ask_agent vom Master beauftragt** ODER direkt im Chat genutzt

### 3. Specialist-Agent
- **Einmalige Aufgaben** (z.B. ISBN-Extractor, MiniMax-Researcher)
- **Eng konfiguriert**: wenige Tools, spezifischer System-Prompt
- **Workspace**: `/var/lib/hydrahive2/workspaces/specialists/<agent-id>/`
- **Nur via ask_agent ansteuerbar** (kein direktes Chat-UI)
- Beispiele: `ISBN Extractor`, `MiniMax-Researcher`

---

## Agent-Konfig-Felder

```json
{
  "id": "uuid",
  "name": "Seven of Nine",
  "owner": "till",                    // User-ID des Besitzers
  "type": "master",                   // master | project | specialist
  "status": "active",                 // active | disabled
  "is_buddy": true,                   // Buddy-Modus (Emote-Hint aktivieren)
  "llm_model": "claude-opus-4-5",    // Primäres Modell
  "fallback_models": [],              // Failover-Modelle
  "max_tokens": 8192,
  "temperature": 1.0,
  "reasoning_effort": null,           // null | "low" | "medium" | "high"
  "tools": ["shell_exec", "file_read", "ask_agent", ...],
  "mcp_servers": [],
  "skills": ["brainstorming", "git-workflow"],
  "disabled_skills": [],
  "system_prompt": "Du bist...",      // Basis-Persona-Prompt
  "compact_model": null,              // null = llm_model verwenden
  "compact_threshold_pct": 80,
  "compact_max_turns": null,
  "compact_tool_result_limit": null,
  "compact_reserve_tokens": null,
  "tool_result_max_chars": 12000,
  "cache_ttl": "1h",
  "max_iterations": 15,
  "project_id": null                  // gesetzt für Project-Agents
}
```

---

## Wo werden Agents gespeichert?

```
/var/lib/hydrahive2/agents/<agent-id>/
├── config.json           # Agent-Konfiguration
├── sessions/             # Session-Daten (Symlink oder direkt)
├── observations/         # Langzeit-Beobachtungen des Agents
├── compressed/           # Komprimierte Contexts
└── soul/                 # (Optional) Soul-Dokument (bei Buddys)
```

---

## Soul-Dokument

Manche Agents (besonders Buddys) haben ein `soul`-Verzeichnis mit:
- Persona-Beschreibung
- Erinnerungen an User-Vorlieben
- Langzeit-Charakter-Eigenschaften
- Wird in System-Prompt integriert

---

## Bootstrap

Beim ersten Start (`bootstrap.py`):
1. Prüft ob Master-Agent für User existiert
2. Falls nicht: Master-Agent mit Default-Config anlegen
3. Workspace-Verzeichnisse anlegen
4. Symlinks setzen (`~/projects/`)

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): Runner lädt Agent-Config zu Beginn jedes Runs
- **→ Buddy** (`09-buddy.md`): Master-Agents sind Buddys
- **→ Projects** (`15-projects.md`): Project-Agents sind an Projekte gekoppelt
- **→ Skills** (`11-skills.md`): `skills`-Liste in Config bestimmt geladene Skills
- **→ Tools** (`02-tools.md`): `tools`-Liste in Config bestimmt erlaubte Tools
