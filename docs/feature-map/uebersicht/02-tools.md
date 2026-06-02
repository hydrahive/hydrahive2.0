# Feature Map: Tools — alle Agent-Tools

> **Modul:** `core/src/hydrahive/tools/`  
> **Was:** Alle Tool-Implementierungen die ein Agent nutzen kann. REGISTRY ist die zentrale Liste.  
> **Warum:** Tools sind die Hände des Agents — ohne sie kann er nur reden.

---

## Tool-System-Übersicht

Jedes Tool ist eine Python-Datei mit:
1. Einer `schema()` Funktion → JSON-Schema für die LLM-API
2. Einer `execute(args, ctx: ToolContext)` Funktion → Ausführung, gibt `ToolResult` zurück
3. Registrierung in `__init__.py` (REGISTRY dict)

```python
# ToolContext enthält:
ctx.session_id    # aktuelle Session
ctx.agent_id      # ausführender Agent
ctx.user_id       # Owner-User
ctx.workspace     # Workspace-Pfad (absolut)
ctx.project_id    # Projekt-ID (wenn gesetzt)
ctx.config        # Tool-Config (aus tool_config-Parameter in run())
```

```python
# ToolResult:
ToolResult(success=True, output="text")
ToolResult.fail("Fehlermeldung")
```

---

## Alle Tools

### Dateisystem & Shell

| Tool | Datei | Was |
|---|---|---|
| `shell_exec` | `shell.py` | Shell-Befehl ausführen. stdout/stderr/exit_code zurück. Timeout konfigurierbar. Läuft im Workspace-Verzeichnis. |
| `file_read` | `file_read.py` | Datei lesen mit Zeilennummern. Supports: offset/limit (Zeilenbereich), grep (Regex-Filter + context_lines). |
| `file_write` | `file_write.py` | Datei schreiben (überschreiben). Parent-Dirs werden automatisch angelegt. |
| `file_patch` | `file_patch.py` | String-Ersetzung in Datei. old_string muss eindeutig sein. replace_all-Flag. |
| `fetch_url` | `fetch_url.py` | HTTP-Request (GET/POST/PUT/PATCH/DELETE). Auth-Injection aus Credential-Store. |
| `web_search` | `web_search.py` | Websuche via SearxNG. Gibt Titel, URL, Snippet. Braucht SearxNG-URL in Settings. |
| `web_browser` | `web_browser.py` | Playwright/Chromium headless. JS-Script in QuickJS-Sandbox. Screenshots möglich. |

### Agent & System

| Tool | Datei | Was |
|---|---|---|
| `ask_agent` | `ask_agent.py` | Anderen Agenten beauftragen via AgentLink. Wartet auf Antwort. Handoff mit Context/Files. |
| `list_projects` | `list_projects.py` | Alle Projekte des Users mit Workspace-Pfad, Repos, Members. |
| `list_skills` | `list_skills.py` | Alle verfügbaren Skills mit Name, Beschreibung, when_to_use. |
| `load_skill` | `load_skill.py` | Skill-Body in Konversation laden. |
| `todo_write` | `todo.py` | Session-Todo-Liste setzen. Status: pending/in_progress/done. |
| `send_mail` | `send_mail.py` | E-Mail senden via SMTP. Config aus Tool-Config (smtp.*). |

### Memory & Wissen

| Tool | Datei | Was |
|---|---|---|
| `read_memory` | `read_memory.py` | Memory-Notizen lesen. Ohne key: Key-Liste. Mit key: Direktzugriff. Gefiltert nach Projekt + Global. |
| `write_memory` | `write_memory.py` | Memory-Notiz speichern. delete=True zum Löschen. expires_at für TTL. Confidence 0-1. |
| `search_memory` | `search_memory.py` | Semantische Memory-Suche (Substring + Confidence-Filter). |
| `read_scratchpad` | `read_scratchpad.py` | Scratchpad lesen (User-Zone + Agent-Zone). Beide Zonen sichtbar. |
| `write_scratchpad` | `write_scratchpad.py` | Nur Agent-Zone des Scratchpads schreiben. User-Zone ist tabu. |

### Datamining / Langzeitgedächtnis

| Tool | Datei | Was |
|---|---|---|
| `datamining_search` | `datamining.py` | Volltextsuche im Mirror (Sessions, Tool-Calls, Texte). |
| `datamining_semantic` | `datamining.py` | Semantische Ähnlichkeitssuche (Embeddings). |
| `datamining_timeline` | `datamining.py` | Zeitstrahl aller Sessions, gruppiert nach Tag. |
| `datamining_today` | `datamining.py` | Was ist heute passiert (Sessions, Requests, Tool-Calls). |

### Gesundheit & Medizin

| Tool | Datei | Was |
|---|---|---|
| `query_fhir_data` | `fhir_data.py` | FHIR R4 Patientenakte lesen. Resource-Types filtern, Volltextsuche. |
| `query_health_data` | `health_data.py` | Apple Health Daten: Schritte, HF, Schlaf, Kalorien. Aggregiert. |

### Multimedial

| Tool | Datei | Was |
|---|---|---|
| `generate_image` | `generate_image.py` | Bild aus Prompt via OpenRouter (GPT-5-image, Gemini). Transparent-Flag → Green-Screen-Keying. |
| `generate_music` | `generate_music.py` | Musik via OpenRouter (Lyria 3). Prompt auf Englisch. |
| `generate_speech` | `generate_speech.py` | TTS via OpenRouter Whisper. Stimmen-Auswahl. |
| `generate_video` | `generate_video.py` | Video via OpenRouter (Kling, Veo, Sora). Async Job-Poll. |
| `analyze_image` | `analyze_image.py` | Bild analysieren via Vision-Modell (Gemini, GPT-4o, Claude). Lokaler Pfad oder URL. |
| `transcribe_audio` | `transcribe_audio.py` | Audio-Datei → Text via OpenRouter Whisper. Auto-Sprach-Detect. |

### Server-Infrastruktur

| Tool | Datei | Was |
|---|---|---|
| `webmin_status` | `webmin_status.py` | Server-Monitoring via Webmin XML-RPC (CPU, RAM, Disk, Load). |
| `webmin_call` | `webmin_call.py` | Beliebige Webmin-Modul-Funktionen aufrufen (cron, net, proc, ...). |

### Interne Hilfsfunktionen (kein Agent-Tool)

| Datei | Was |
|---|---|
| `_openrouter_media.py` | HTTP-Client für OpenRouter Bild/Musik-Requests |
| `_openrouter_video.py` | Poll-Loop für async Video-Jobs |
| `_openrouter_transcribe.py` | File-Upload + Transkription via OpenRouter |
| `_image_keying.py` | Green-Screen-Keying für transparente PNG-Bilder |
| `_memory_io.py` | Memory-Lese-/Schreiblogik (intern) |
| `_memory_model.py` | Memory-Datenmodell (Pydantic) |
| `_memory_store.py` | Memory-Persistenz (JSON-Dateien per Agent) |
| `_observations.py` | Observation-Speicherung (Langzeitbeobachtungen) |
| `_compress.py` | compress_session-Tool (Context-Kompression manuell) |
| `_compress_prompts.py` | Prompts für compress_session |
| `_compress_storage.py` | Persistenz für Compress |
| `_crystallize.py` | crystallize-Tool (Wissen aus Session destillieren) |
| `_crystallize_prompts.py` | Prompts für crystallize |
| `_crystallize_storage.py` | Persistenz für Crystallize |
| `_sessions.py` | session_start/session_end Events |
| `_launcher.py` | Tool-Launcher-Hilfsfunktionen |
| `_path.py` | Workspace-Pfad-Validierung (Pfade dürfen Workspace nicht verlassen) |
| `_webmin.py` | Webmin XML-RPC Client |
| `base.py` | ToolContext, ToolResult Basisklassen |

---

## REGISTRY — wie Tools registriert werden

```python
# tools/__init__.py
REGISTRY: dict[str, ToolDefinition] = {
    "shell_exec": ToolDefinition(schema=shell.schema, execute=shell.execute),
    "file_read": ToolDefinition(...),
    ...
}

def schemas_for(tool_names: list[str]) -> list[dict]:
    """Gibt JSON-Schemas für die angeforderten Tools zurück."""
```

- Jeder Agent hat eine `tools`-Liste in seiner Config
- Nur gelistete Tools sind dem Agent erlaubt (Allowlist)
- Der Runner ruft `schemas_for(local_tools)` auf → LLM sieht nur diese Schemas
- Im Dispatcher: `if tool_name not in allowed_tools: → ToolResult.fail()`

---

## Tool-Pfad-Sicherheit

`_path.py` validiert alle Dateipfade:
- Pfad muss absolut sein oder relativ zum Workspace aufgelöst werden
- Pfad darf Workspace nicht verlassen (kein `../../etc/passwd`)
- Bei Verstoß: `ToolResult.fail("Pfad außerhalb Workspace")`

---

## Plugin-Tools vs. Built-in-Tools

- **Built-in**: In `REGISTRY`, immer verfügbar wenn in Agent-Config
- **Plugin-Tools**: Präfix `plugin__`, geladen via `plugin_bridge`
- **MCP-Tools**: Präfix `mcp__`, geladen via `mcp_bridge`

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): Dispatcher ruft Tools auf
- **→ Plugins** (`10-plugins.md`): Plugin-Tools ergänzen REGISTRY
- **→ MCP** (`13-mcp.md`): MCP-Tools haben eigene Bridge
- **→ Credentials** (`32-credentials.md`): fetch_url nutzt Auth-Injection
- **→ AgentLink** (`14-agentlink.md`): ask_agent ist das wichtigste Orchestrierungs-Tool
- **→ Memory** (`17-memory.md`): read/write/search_memory
- **→ Datamining** (`16-datamining.md`): datamining_* Tools
