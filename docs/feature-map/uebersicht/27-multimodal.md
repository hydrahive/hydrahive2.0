# Feature Map: Multimodal — TTS, Bildgenerierung, Video, Musik, Transkription

> **Modul:** `core/src/hydrahive/tools/` (Media-Tools)  
> **Konfiguration:** `llm/media_models.py` — welches Modell für welche Media-Task  
> **Was:** Alles was nicht Text ist: generieren, analysieren, transkribieren.  
> **Warum:** Agents können Bilder sehen, Sprache ausgeben, Videos erstellen.

---

## Media-Tools Übersicht

| Tool | Modul | Provider |
|---|---|---|
| `generate_image` | `tools/generate_image.py` | OpenRouter (DALL-E, Stable Diffusion, Midjourney, ...) |
| `analyze_image` | `tools/analyze_image.py` | OpenRouter (Vision-Modelle: GPT-4o, Gemini, Claude) |
| `generate_speech` | `tools/generate_speech.py` | OpenRouter (TTS-Modelle) |
| `generate_music` | `tools/generate_music.py` | OpenRouter (Lyria 3, ...) |
| `generate_video` | `tools/generate_video.py` | OpenRouter (async Jobs) |
| `transcribe_audio` | `tools/transcribe_audio.py` | OpenRouter (Whisper) |

---

## Media-Models-Config

```python
# llm/media_models.py — welche Modelle für Media-Tasks

MEDIA_MODELS = {
    "image_generation": "openai/gpt-5-image-mini",    # Default: günstig
    "image_vision": "google/gemini-2.5-flash",         # Default: schnell
    "tts": "openai/tts-1",                              # Default TTS
    "music": "google/lyria-3-pro-preview",              # Default Musik
    "video": "kling/kling-video-v2-master",             # Default Video
    "transcription": "openai/whisper-large-v3",        # Default Transcription
}
```

Frontend-Konfig: `features/llm/MediaModelsSection.tsx`

---

## Generiertes-Dateien-Pfad

```
/var/lib/hydrahive2/workspaces/<workspace-id>/generated/
├── <uuid>.png       # generierte Bilder
├── <uuid>.mp3       # TTS-Ausgaben
├── <uuid>.mp4       # generierte Videos
└── <uuid>.mp3       # generierte Musik
```

Agents erhalten den relativen Pfad zur Datei nach der Generierung.
Frontend zeigt Mediendateien via `MediaPreview.tsx` direkt im Chat.

---

## generate_image — Details

```python
generate_image(
    prompt="Ein futuristischer Schreibtisch mit Hologrammen",
    width=1024,
    height=1024,
    transparent=True,     # Grüner Hintergrund → Server-seitiger Chroma-Key
    model="openai/gpt-5-image-mini"  # Optional override
)
→ {path: "generated/<uuid>.png", url: "/files/generated/<uuid>.png"}
```

**Transparent-Flag:** Motiv wird auf Chromagreen generiert, Server keyt Hintergrund raus → echtes PNG mit Alpha.
Für Fotos/Hintergründe: `transparent=False`.

**Bekanntes Problem:** Tool-Result enthält manchmal falschen Dateipfad (halluzinierter Name). Reale Datei liegt unter UUID-Name. Fix: Datei nach Generierung per `ls` verifizieren.

---

## generate_speech — Details

```python
generate_speech(
    text="Borg-Kollektiv bestätigt.",
    voice="nova",           # Stimmen: alloy, echo, fable, onyx, nova, shimmer
    model="openai/tts-1"
)
→ {path: "generated/<uuid>.mp3"}
```

Frontend spielt Audio direkt im Chat ab (Audio-Player-Bubble).

---

## generate_video — Details

```python
generate_video(
    prompt="Ein Hydra-Roboter schwebt durch den Weltraum",
    duration=5,
    aspect_ratio="16:9",
    width=1280,
    height=720,
    model="kling/kling-video-v2-master"
)
→ Async Job → poll bis fertig → {path: "generated/<uuid>.mp4"}
```

Generierung dauert 15–90s je nach Modell. Tool pollt automatisch.

---

## transcribe_audio — Details

```python
transcribe_audio(
    file="/path/to/audio.mp3",
    language="de"           # Optional: Auto-detect wenn leer
)
→ {text: "Transkribierter Text..."}
```

Nützlich für heruntergeladene Voice-Messages (WhatsApp), Sprach-Notizen.

---

## analyze_image — Details

```python
analyze_image(
    image="/path/to/image.png",  # Oder https:// URL
    question="Was steht auf dem Rezept?",
    model="google/gemini-2.5-flash"
)
→ {answer: "Auf dem Rezept steht..."}
```

---

## Verwandte Subsysteme

- **→ LLM** (`12-llm.md`): OpenRouter-Client, der für Media-Requests genutzt wird
- **→ Tools** (`02-tools.md`): Media-Tools sind Teil der Tool-REGISTRY
- **→ Chat UI** (`19-frontend-chat.md`): MediaPreview.tsx
