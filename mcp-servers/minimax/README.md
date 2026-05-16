# HydraHive MiniMax MCP-Server

Wrапpt das offizielle `minimax-mcp` Paket und stellt folgende Tools
für HydraHive-Agenten bereit:

| Tool | Beschreibung |
|---|---|
| `text_to_audio` | TTS — Text zu natürlicher Sprache |
| `generate_image` | Bild aus Text-Prompt generieren |
| `generate_video` | Video aus Prompt oder Bild (Hailuo-02, 6s/10s, 768P/1080P) |
| `voice_clone` | Stimme aus Audio-File klonen |
| `voice_design` | Stimme aus Text-Beschreibung erstellen |
| `music_generation` | Musik generieren (music-1.5) |

## Installation

```bash
./install
```

Voraussetzung: `MINIMAX_API_KEY` in der HydraHive LLM-Config
(Provider `minimax` in `llm.json`) oder als Umgebungsvariable.

## Starten

```bash
/opt/hydrahive2/.venv/bin/python server.py
```

## Optionale Umgebungsvariablen

| Variable | Default | Beschreibung |
|---|---|---|
| `MINIMAX_MCP_BASE_PATH` | `/tmp/minimax-mcp` | Output-Verzeichnis für generierte Dateien |
| `MINIMAX_API_HOST` | `https://api.minimax.io` | API-Host (Global oder China) |
| `MINIMAX_API_RESOURCE_MODE` | `url` | `url` = Ergebnisse als URL, `local` = Ergebnisse als Datei |

## Text-to-Speech Parameter

- `model`: `speech-01-turbo` (schnell) oder `speech-01-hd` (hohe Qualität)
- `languageBoost`: Sprach-Erkennung verbessern — `German`, `English`, `auto` (Standard), und 17 weitere
- `subtitleEnable`: Untertitel-Datei mitgenerieren (nur mit `speech-01-turbo` oder `speech-01-hd`)

## Image-Generierung Parameter

- `aspectRatio`: `1:1`, `16:9`, `4:3`, `3:2`, `2:3`, `3:4`, `9:16`, `21:9`
- `n`: Anzahl Bilder (1-9)
- `subjectReference`: Pfad oder URL zu einem Referenz-Bild für Character-Konsistenz

## Video-Generierung Parameter

- `prompt` oder `first_frame_image` (mind. eines erforderlich)
- Modell: `MiniMax-Hailuo-02`
- Dauer: 6s oder 10s
- Auflösung: 768P oder 1080P
