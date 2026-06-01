# Built-in Tools — Architektur

**Last Updated:** 2026-06-01

Tools sind Agent-callable Funktionen im Runner. Der Agent spricht sie über `tool_use`-Blöcke
an, der Runner dispatched sie + streamt Ergebnisse zurück. Alle neuen Tools sollen selbst
in `core/src/hydrahive/tools/` leben, nicht als Plugins.

## Tool-Basis (Abstraktion)

**Datei:** `tools/base.py`

```python
class Tool:
    name: str
    schema: dict  # JSON-Schema für Parameter
    description: str
    
    async def execute(context: ToolContext) -> ToolResult
```

- `ToolContext` — entpackt User-ID, Session, Agent-Config, Settings
- `ToolResult` — Text-Block, Success/Error-Flag
- Synchrone Ausführung im Whitebox-Modus (Agent läuft in separatem Process), oder asynchron via `await`

## Kategorien

### Datei-Operationen
- `file_write.py` — Datei schreiben (mit Guard: Workspace-Pfad-Prüfung, Größenlimit)
- `file_read.py` — Datei lesen
- `file_delete.py` — Datei löschen

### Netzwerk/HTTP
- `fetch_url.py` — HTTP GET/POST (mit SSRF-Schutz für private IP-Ranges)
- `http_request.py` — Beliebige HTTP-Requests

### System/Shell
- `shell.py` — Shell-Befehle ausführen (stdin/stdout/stderr, Timeout, Root-Check)

### Datamining (Beobachtungen)
- `datamining_timeline.py` — Agenten-History + globale Events zeitgeordnet
- `datamining_search.py` — Semantische Suche über Embedding-Modell
- `datamining_observe.py` — Neue Beobachtungen in den Store schreiben

### Multimodal (OpenRouter APIs, neu 2026-06)
- **Vision:** `analyze_image.py` — Bild mit Vision-Modell analysieren (Gemini, GPT-4o, Claude)
  - Input: lokaler Dateipfad (Base64) oder http(s)-URL
  - Modell: konfigurierbar, Default `google/gemini-2.5-flash`
  - Output: Textantwort auf Frage
  
- **Video:** `generate_video.py` — Text→Video über OpenRouter async Jobs-API
  - Modelle: Kling v2 (default, schnell), Veo 3.1, Sora 2 Pro, Hailuo 2.3
  - Poll-Loop: max 300s, exponentiell backoff (5s→10s→20s)
  - Output: speichert Video im Workspace, zeigt URL
  - Braucht: OpenRouter API-Key
  
- **Audio:** `transcribe_audio.py` — Audio→Text via Whisper
  - Input: lokale Datei (mp3, mp4, m4a, webm, ogg, wav, flac)
  - Sprache: optional (Auto-Detect Standard)
  - Modell: Default `openai/whisper-large-v3`, konfigurierbar
  - Output: Transkription als Text
  - Braucht: OpenRouter API-Key

### Text-Generierung
- `generate_image.py` — Text→Bild (OpenRouter DALL-E / Flux)
- `generate_music.py` — Text→Musik (Google Lyria, HunYuan Music)

### Scratchpad
- `read_scratchpad.py` — Globale Mensch→Agent-Zone + Agent-Zone lesen
- `write_scratchpad.py` — Agent-Zone schreiben (Mensch-Zone read-only für Agent)

## Registrierung & Discovery

**Datei:** `tools/_registry.py`

Beim Runner-Start wird die Tool-Registry aus den importierten Klassen gebaut:

```python
def load_tools(config: dict) -> dict[str, Tool]:
    # Imports aller `@tool`-Klassen
    # Filter: nur wenn API-Key vorhanden (provider_credentials)
    # Return: {name: Tool-Instanz}
```

Tools ohne konfigurierte Credentials werden **nicht** registriert — Agent sieht sie nicht.

## API-Exposure

**Datei:** `api/routes/tools.py`

- `GET /api/tools` — Liste aller verfügbaren Tools für aktuellen User + Session
  - Schema, Name, Beschreibung
  - Filtered nach verfügbaren Credentials

- `POST /api/tools/{name}/test` — Optional: Test-Endpunkt (z.B. für Connection-Check)
  - Admin-only meist
  - Nützlich für Konfiguration

## Fehlerbehandlung & Timeouts

- Tool-Fehler zurück als `ToolResult(success=False, error="..."`
- Runner fangt Exceptions auf, nicht der Caller
- Timeout: pro Tool konfigurierbar in `tool_config` eines Agents (Default je Tool unterschiedlich)
- Kein `RuntimeError` raus an den Client — Error-Text nett verpackt

## Media-Modelle & Tool-Parameter

Viele Multimodal-Tools brauchen ein Modell-Auswahl. Muster seit 2026-06:

**im Tool:**
```python
model = get_media_model("image", config)  # Default aus llm.json media_models.image
# Tool-Parameter model überschreibt
```

**im Tool-Schema:**
```json
{
  "model": {
    "type": "string",
    "description": "OpenRouter-Modell, Default: google/gemini-2.5-flash"
  }
}
```

**Frontend-Picker:** `llm/MediaModelsSection.tsx` — einfach bei Agent-Config ändern.

## Testen

**Unit-Test Pattern:**
```python
# tests/test_tools_*.py
@pytest.mark.asyncio
async def test_file_write_creates_file():
    ctx = ToolContext(user_id="test", ...)
    result = await file_write.execute(
        ctx, path="/tmp/test", content="hello"
    )
    assert result.success
```

**Integration-Tests:** gegen echte APIs (OpenRouter, lokale File-Ops)
- Seeded mit Test-Credentials
- Mocking optional für Offline-Tests

## Beste Praktiken

1. **Ein Tool = eine Verantwortung** — `analyze_image.py` tut nur Vision, nicht auch andere APIs
2. **Workspace-Pfade validieren** — `file_write` muss sicherstellen dass man nicht `/etc` schreiben kann
3. **Dateigrößen begrenzen** — Input (Datei zum Lesen) + Output (Response) Guards
4. **Timeout + Async-Support** — Für lange Operationen (Video-Poll) nicht blockieren
5. **Error-Messages für Humans** — nicht "exception.traceback", sondern "Datei nicht gefunden"
6. **Credentials nicht in Log** — `API_KEY` wird nie geloggt (sanitize in logs)
7. **Fallbacks wo möglich** — Media-Modelle mit Fallback-Liste falls Live-Fetch fehlt

## Zusammenfassung

| Tool | Typ | Input | Output | Braucht | Neu |
|---|---|---|---|---|---|
| `file_read` | File | Pfad | Text | — | nein |
| `file_write` | File | Pfad + Content | Success | — | nein |
| `file_delete` | File | Pfad | Success | — | nein |
| `shell` | System | Befehl | stdout/stderr | — | nein |
| `fetch_url` | HTTP | URL | Inhalt | — | nein |
| `datamining_search` | Memory | Query | Results | Embed-Modell | nein |
| `datamining_timeline` | Memory | Filter | Events | — | nein |
| `analyze_image` | Vision | Bild + Query | Text | OpenRouter | **ja, 2026-06** |
| `generate_image` | Image | Prompt | URL | OpenRouter | nein |
| `generate_video` | Video | Prompt | URL | OpenRouter | **ja, 2026-06** |
| `generate_music` | Audio | Prompt | URL | OpenRouter | nein |
| `transcribe_audio` | Audio | Datei | Text | OpenRouter | **ja, 2026-06** |
| `read_scratchpad` | Scratchpad | — | Text | — | ja (2026-05-31) |
| `write_scratchpad` | Scratchpad | Text | Success | — | ja (2026-05-31) |
