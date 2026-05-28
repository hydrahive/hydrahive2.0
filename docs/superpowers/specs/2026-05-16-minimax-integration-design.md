# MiniMax Integration Design — HydraHive2

**Datum:** 2026-05-16  
**Status:** Approved

---

## 1. Ziele und Scope

### Was gebaut wird

1. **Mini-Agent-Analyse** — MiniMax's eigenen Mini-Agent-Source lesen, Muster dokumentieren, Empfehlungen für HydraHive-Agenten formulieren
2. **Interleaved Thinking aktivieren** — M2/M2.7's wichtigstes Agentic-Feature ist im bestehenden `minimax_anthropic_call()` noch nicht verdrahtet
3. **Modell-Katalog-Update** — `MiniMax-M2.1` (erschienen Dez 2025) fehlt noch
4. **MiniMax-MCP-Server** — Neues `mcp-servers/minimax/` für Image Gen, Video Gen, Voice Clone, Voice Design, Music Gen via offiziellem `minimax-mcp` Paket
5. **Agenten-Profile** — Fertige HydraHive-Agenten-Konfigurationen die MiniMax-Backend + MiniMax-MCPs kombinieren

### Was NICHT in Scope ist

- Eigene MiniMax-Modelle lokal hosten
- TTS-Pfad ändern (bleibt bei `mmx-cli` / `voice/tts.py` — funktioniert)
- Mini-Agent als eigenständiges System betreiben
- MiniMax-China-Endpoint (`api.minimaxi.com`) — nur Global-Platform

---

## 2. Bestehende MiniMax-Integration (Stand heute)

Die MiniMax-Backend-Integration ist bereits weit fortgeschritten — das ist wichtig um Doppelarbeit zu vermeiden.

### Was bereits funktioniert

| Komponente | Datei | Status |
|---|---|---|
| LLM-Calls (Anthropic-kompatibler Pfad) | `runner/_llm_bridge_backends.py` | ✅ fertig |
| Streaming | `runner/llm_bridge_stream.py` | ✅ fertig |
| Model-Detection `is_minimax_model()` | `llm/_anthropic.py` | ✅ fertig |
| Image-Format-Konvertierung | `llm/_anthropic.py` | ✅ fertig |
| TTS via `mmx-cli` (synthesize_mp3, to_ogg, list_voices) | `voice/tts.py` | ✅ fertig |
| Usage-Tracking | `llm/_minimax_usage.py` | ✅ fertig |
| Embeddings | `llm/embed.py` | ✅ fertig |
| API-Key-Verwaltung via `llm.json` Provider `minimax` | `llm/client.py` | ✅ fertig |

### API-Endpunkt

- Global: `https://api.minimax.io/anthropic`
- Anthropic-SDK mit `base_url` + `Authorization: Bearer <key>` Header
- Kein OAuth, kein Identity-System-Block (MiniMax erwartet den nicht)

### Bekannte API-Einschränkungen

Folgende Anthropic-Parameter werden von MiniMax **ignoriert** (laut API-Doku):
- `top_k`, `stop_sequences`, `service_tier`
- `mcp_servers`, `context_management`, `container`
- Einige Anthropic-Beta-Features (cache-editing, fine-grained-tool-streaming)

---

## 3. MiniMax Modell-Referenz

### Modelle auf platform.minimax.io (Anthropic-kompatibler Pfad)

| Modell | API-Identifier | Context | Max Output | tool_use | Preise (Input/Output per M Token) |
|---|---|---|---|---|---|
| MiniMax-Text-01 | `MiniMax-Text-01` | 1M | — | ✅ | $0.20 / $1.10 |
| MiniMax-M1 | `MiniMax-M1` | 1M | — | ✅ | $0.40 / $2.20 |
| MiniMax-M2 | `MiniMax-M2` | 197K | — | ✅ | $0.255 / $1.00 |
| MiniMax-M2.1 | `MiniMax-M2.1` | 205K | — | ✅ | $0.30 / $1.20 |
| MiniMax-M2.7 | `MiniMax-M2.7` | 204K | 131K | ✅ | $0.279 / $1.20 |

### Modell-Charakteristika

**MiniMax-Text-01** — Günstigstes Modell mit 1M Context. Gut für einfache Chat-/Zusammenfassungs-Aufgaben. Kein Reasoning.

**MiniMax-M1** — Open-Weight Reasoning-Modell. 1M Context. Stärke: lang-context Verständnis, komplexe Analyse. Teurer als M2-Familie. Kein Interleaved Thinking.

**MiniMax-M2** — Open-Source. 197K Context. Gut für Coding und Tool-Use. Interleaved Thinking unterstützt.

**MiniMax-M2.1** — Verbesserte M2-Variante (Dez 2025). Speziell für Multi-Sprach-Programmierung: Rust, Java, Go, C++, Kotlin, Objective-C, TypeScript, JavaScript. 205K Context. Interleaved Thinking unterstützt. **Fehlt noch im Katalog.**

**MiniMax-M2.7** — Flagship Agentic Model (Mai 2026). MoE-Architektur: 230B Parameter, 10B aktiv pro Token, 256 Experts. 204K Context, bis 131K Output. Interleaved Thinking mit signifikanten Benchmark-Gewinnen. Bestes Modell für komplexe Agenten-Workflows. Multi-Agent Collaboration. 97% Skill-Adherence bei 40+ komplexen Skills.

### Verfügbarkeit über andere Provider

MiniMax-Modelle sind auch über NVIDIA NIM, OpenRouter, Together AI, AWS Bedrock verfügbar — bereits im Katalog unter `nvidia_nim/minimaxai/minimax-m2.*`. Für HydraHive-Agenten gilt: **direkter MiniMax-Pfad** (`api.minimax.io`) bevorzugen wegen voller Feature-Unterstützung.

---

## 4. Interleaved Thinking — Das wichtigste Feature

### Was es ist

Interleaved Thinking bedeutet: das Modell denkt zwischen jedem Tool-Call nach. Denk-Blöcke werden über Turn-Grenzen hinweg erhalten und dem Modell beim nächsten Turn zurückgegeben. Das Modell führt seinen Reasoning-Faden weiter statt bei jedem Tool-Result von vorne zu beginnen.

**Plan → Act → Reflect → Act → Reflect …**

### Warum es wichtig ist

Ohne Interleaved Thinking (klassischer Tool-Loop):
```
User-Turn → Denken → Tool-Call → [Denken VERGESSEN] → nächster Turn → Denken von vorne
```

Mit Interleaved Thinking:
```
User-Turn → Denken → Tool-Call → [Denken ERHALTEN] → nächster Turn → Denken fortsetzen
```

Gemessene Benchmark-Gewinne (M2.7, Interleaved vs. kein Interleaved):
- SWE-Bench Verified: 69.4% vs. 67.2% (+3.3%)
- BrowseComp: 44.0% vs. 31.4% (+40.1%)

### Aktivierung

Gleiche Syntax wie Anthropic Extended Thinking:

```python
kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
```

Empfohlene Budget-Werte für MiniMax:

| Effort | budget_tokens | Einsatz |
|---|---|---|
| low | 1 024 | Schnelle Tool-Calls, einfache Entscheidungen |
| medium | 4 096 | Standard Agentic-Loops |
| high | 16 384 | Komplexe mehrstufige Planung |

### Aktueller Stand im Code

`minimax_anthropic_call()` in `runner/_llm_bridge_backends.py` hat **keinen `reasoning_effort`-Parameter** — Interleaved Thinking wird nie aktiviert. Das ist die wichtigste Lücke.

### Was zu ändern ist

1. `minimax_anthropic_call()` bekommt `reasoning_effort: str | None = None`
2. `apply_thinking_budget(kwargs, reasoning_effort)` wird aufgerufen (Funktion existiert bereits in `llm/_anthropic.py`)
3. `llm_bridge.py` `call_with_tools()` übergibt `reasoning_effort` an `minimax_anthropic_call()`
4. Analog für `_stream_providers.py`

**Achtung:** Bei MiniMax gilt `temperature=1.0` nur wenn Thinking aktiviert ist — gleiches Verhalten wie Anthropic. `apply_thinking_budget()` setzt das bereits automatisch.

---

## 5. Modell-Katalog-Update

### MiniMax-M2.1 hinzufügen

**Datei:** `core/src/hydrahive/llm/_catalog_data.py`

```python
"MiniMax-M2.1": {"context_window": 205_000, "tool_use": True, "category": "chat", "family": "minimax"},
```

**Liste** in `_KNOWN_MODELS["minimax"]` ergänzen:
```python
"minimax": ["MiniMax-Text-01", "MiniMax-M2", "MiniMax-M2.1", "MiniMax-M2.7", "MiniMax-M1"],
```

### Preise

Falls Pricing-Daten im Katalog gepflegt werden: M2.1 ist $0.30 / $1.20 per M Token.

---

## 6. MiniMax-MCP-Server

### Warum ein eigener MCP-Server

Die bestehende TTS-Integration (`voice/tts.py`) nutzt `mmx-cli` als Subprocess — das ist ein separater Pfad für WhatsApp-Voice-Notes. Der MCP-Pfad ist für Agenten gedacht: ein Agent soll zur Laufzeit MiniMax-Medien-Fähigkeiten als Tools aufrufen können.

Neue Fähigkeiten die noch gar nicht in HydraHive vorhanden sind:
- Image-Generierung
- Video-Generierung
- Voice Clone (aus Audio-File)
- Voice Design (aus Text-Beschreibung)
- Music Generation

### Verzeichnis-Struktur

```
mcp-servers/minimax/
├── pyproject.toml       # depends on minimax-mcp
├── server.py            # Wrapper/Launcher
├── README.md
├── install
└── uninstall
```

### Abhängigkeit

Das offizielle `minimax-mcp` PyPI-Paket wird als Dependency eingebunden — kein eigenes Tool-Implementieren.

```toml
[project]
name = "hydrahive-minimax-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "minimax-mcp>=0.1",
]
```

### Tools die der MCP-Server exponiert

| Tool | Beschreibung | Wichtige Parameter |
|---|---|---|
| `text_to_audio` | TTS — natürliche Sprache | `text`, `voice_id`, `model` (`speech-01-turbo` oder `speech-01-hd`), `languageBoost` (20+ Sprachen), `channel` (1/2), `subtitleEnable` |
| `generate_image` | Bild aus Text-Prompt | `prompt`, `aspectRatio` (1:1, 16:9, 4:3, 3:2, 2:3, 3:4, 9:16, 21:9), `n` (1-9), `promptOptimizer`, `subjectReference` (Charakter-Referenz-Bild) |
| `generate_video` | Video aus Prompt/Bild | `prompt` oder `first_frame_image` (mind. eines erforderlich), Modell `MiniMax-Hailuo-02`, Dauer 6s/10s, Auflösung 768P/1080P |
| `voice_clone` | Stimme aus Audio-File klonen | `audio_file` (Pfad oder URL) |
| `voice_design` | Stimme aus Text-Beschreibung erstellen | `description` (z.B. "junge Frau, warmherzig, etwas heiser") |
| `music_generation` | Musik generieren | `prompt`, Model `music-1.5` |

### Umgebungsvariablen

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `MINIMAX_API_KEY` | ✅ | API-Key (aus `llm.json` Provider `minimax`) |
| `MINIMAX_MCP_BASE_PATH` | — | Lokaler Output-Ordner für Dateien (Standard: `/tmp`) |
| `MINIMAX_API_HOST` | — | `https://api.minimax.io` (Global, Standard) |
| `MINIMAX_API_RESOURCE_MODE` | — | `url` (Standard) oder `local` — ob Ergebnisse als URL oder lokale Datei geliefert werden |

Der `MINIMAX_API_KEY` wird beim Start des MCP-Servers aus `llm.json` gelesen und als ENV-Variable gesetzt, damit kein zweiter Konfigurations-Ort entsteht.

### Install-Script

Analog zu anderen MCP-Servern: pip-install in das HydraHive-venv, MCP-Config-Eintrag schreiben.

---

## 7. Agenten-Profile

### Profil-Struktur (HydraHive-DB)

Jedes Profil ist ein Agent-Config-Objekt mit:
- `name`: Anzeigename
- `model`: MiniMax-Modell-ID
- `reasoning_effort`: `null` / `"low"` / `"medium"` / `"high"`
- `system_prompt`: Optimierter System-Prompt für MiniMax
- `mcps`: Liste der MCP-Server-IDs
- `tools`: Erlaubte HydraHive-Tools

### MiniMax-Coder (Empfehlung für Coding-Aufgaben)

```json
{
  "name": "MiniMax-Coder",
  "model": "MiniMax-M2.7",
  "reasoning_effort": "medium",
  "system_prompt": "Du bist ein präziser Coding-Assistent. Denke vor jedem Tool-Call kurz nach welche Informationen du noch brauchst. Plane in Schritten. Nach jedem Tool-Result: evaluiere ob dein Plan noch stimmt.",
  "mcps": ["minimax_search"],
  "tools": ["shell_exec", "read_file", "write_file", "list_dir"]
}
```

### MiniMax-Creative (Medien-Generierung)

```json
{
  "name": "MiniMax-Creative",
  "model": "MiniMax-M1",
  "reasoning_effort": null,
  "system_prompt": "Du bist ein kreativer Medien-Assistent. Nutze die verfügbaren Tools um Bilder, Videos, Musik und Sprache zu erzeugen.",
  "mcps": ["minimax_mcp"],
  "tools": ["read_file", "write_file"]
}
```

### MiniMax-Researcher (Recherche + Analyse)

```json
{
  "name": "MiniMax-Researcher",
  "model": "MiniMax-M2.7",
  "reasoning_effort": "high",
  "system_prompt": "Du bist ein gründlicher Recherche-Agent. Durchsuche Quellen systematisch. Halte Zwischenergebnisse fest. Überprüfe Fakten bevor du antwortest.",
  "mcps": ["minimax_search"],
  "tools": ["read_file", "write_file", "list_dir"]
}
```

### System-Prompt-Richtlinien für MiniMax-Modelle

MiniMax-Modelle reagieren gut auf:
- Explizite Schritt-für-Schritt-Anweisungen
- Kurze, präzise Instruktionen (kein Identity-Block nötig — MiniMax ignoriert den)
- Hinweise zum Nutzen von Interleaved Thinking ("Denke vor jedem Tool-Call nach")
- Deutschen oder englischen Text — beide unterstützt

MiniMax-Modelle reagieren schlecht auf:
- Sehr lange System-Prompts mit vielen Regeln (erhöht Latenz ohne Mehrwert)
- Anthropic-spezifische Instruktionen (Claude-Code-Persona, OAuth-Flows)

---

## 8. Mini-Agent Analyse

### Was zu lesen ist

Auf GitHub: `MiniMax-AI/Mini-Agent`

Fokus-Punkte:
1. **Session Note Tool** — Wie persistiert der Agent Wissen über Session-Grenzen? Format des Scratchpads, wann wird es gelesen/geschrieben?
2. **Context-Compaction** — Wann triggert automatische Zusammenfassung? Welcher Prompt wird dafür verwendet? Wie viel Context wird behalten?
3. **Agent-Loop** — Genaue Reihenfolge von Check → Think → Act → Feedback. Fehler-Handling im Loop.

### Output

`docs/research/minimax-mini-agent-analysis.md` — kompaktes Dokument mit:
- Key-Patterns (3-5 Punkte)
- Direkte Empfehlungen für HydraHive-Agenten-Konfigurationen
- Code-Snippets aus Mini-Agent mit Quellenangabe

---

## 9. Implementierungs-Reihenfolge

1. **Mini-Agent-Analyse** (kein Code, 1 Dokument)
2. **Interleaved Thinking aktivieren** (`_llm_bridge_backends.py`, `llm_bridge.py`, `llm_bridge_stream.py`) — kleiner Diff, hoher Impact
3. **M2.1 in Katalog** (`_catalog_data.py`) — 2 Zeilen
4. **MiniMax-MCP-Server** (`mcp-servers/minimax/`) — neue Komponente
5. **Agenten-Profile** — DB-Seeds + Dokumentation

---

## 10. Tests

### Interleaved Thinking

- Test in `core/tests/test_llm_calls_logging.py` oder neues `test_minimax_thinking.py`
- Prüfen: wenn `reasoning_effort="medium"` gesetzt, enthält die Request `thinking.budget_tokens=4096`
- Prüfen: bei `reasoning_effort=None` kein `thinking`-Block in der Request

### MiniMax-MCP

- Smoke-Test: Server startet und listet Tools korrekt auf
- Kein API-Call-Test (würde echte Tokens kosten)

### Katalog

- Existing Katalog-Tests prüfen ob M2.1 korrekt erkannt wird

---

## Referenzen

- [MiniMax-AI/Mini-Agent](https://github.com/MiniMax-AI/Mini-Agent)
- [MiniMax-AI/MiniMax-MCP](https://github.com/MiniMax-AI/MiniMax-MCP)
- [MiniMax Platform API Docs](https://platform.minimax.io/docs)
- [Interleaved Thinking Blog](https://www.minimax.io/news/why-is-interleaved-thinking-important-for-m2)
- [MiniMax M2.7 Announcement](https://www.minimax.io/news/minimax-m27-en)
