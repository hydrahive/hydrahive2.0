# Spec: Lokale Video-/Bild-Backends (ComfyUI + sd-server)

Status: DRAFT — Design-Freigabe ausstehend
Autor: Buddy (mit till)
Datum: 2026-07-25

## Problem

Die Video- (und Bild-)Generierung im Atelier ist hart auf **OpenRouter**
verdrahtet (`llm/media_models.py` → `list_video_models`, `tools/_openrouter_video.py`).
Der Video-Dialog kann deshalb ausschließlich OpenRouter-Modelle anbieten.

Ein Kunde betreibt **zwei verschiedene lokale Backends** übers Netz:

| Node | Backend | API | Port (Bsp.) | Modelle |
|------|---------|-----|-------------|---------|
| Muskeln1 (.78) | **ComfyUI** + LTX-2.3 22B | HTTP-Workflow-API | 8189 | LTX-2.3 (T2V/T2V+A/I2V), SDXL/Flux (Bild) |
| Muskeln2 (.81) | **stable-diffusion.cpp** (`sd-server`) | HTTP-API (`--host 0.0.0.0`) | 8080 | LTX-2.3 GGUF (Video), RealVisXL (Bild) |

Ziel: Der User soll **über die GUI** lokale Backends anlegen und deren Modelle/
Workflows im Video-Dialog auswählen können — neben den OpenRouter-Modellen.
Flexibel genug, dass ein **drittes** Backend später nicht alles bricht.

### Wichtig: ComfyUI ist EINE Instanz, Kategorie steckt im Workflow

ComfyUI ist **kein Programm pro Aufgabe**, sondern ein Node-Graph-System. Bild
UND Video laufen über **dieselbe Instanz auf einem Port** (Muskeln1: 8189).
Ob Bild oder Video herauskommt, entscheidet **allein der Workflow** (die Nodes):

- **Bild:** `KSampler → VAEDecode → SaveImage`
- **Video:** `KSampler → VAEDecode → SaveAnimatedWEBP` (+ Audio-Pfad bei T2V+A)

Design-Konsequenz: Die **Kategorie (image/video) ist eine Eigenschaft des
Workflows, nicht des Backends**. Ein einziges konfiguriertes ComfyUI-Backend
kann daher sowohl Bild- als auch Video-Workflows bereitstellen — sie tauchen je
nach `category` im Bild- bzw. Video-Dialog auf. Das output-Node bestimmt zudem
die Ergebnis-Behandlung (SaveImage→PNG direkt; SaveAnimatedWEBP→WebP-Frames→
ffmpeg→MP4).

## Nicht-Ziele (bewusst ausgeschlossen)

- Kein SSH-/CLI-Ausführungspfad. Nur HTTP-erreichbare Dienste (`sd-cli` direkt
  wird NICHT unterstützt — dafür gibt es `sd-server`).
- Keine automatische Workflow-Konvertierung UI→API-Format in v1 (der User
  hinterlegt Workflows im **API-Format**; ComfyUI: „Save (API Format)"). Ein
  optionaler Konverter kann später folgen.
- Keine GPU-/VRAM-Verwaltung durch HydraHive — das regelt das Backend selbst.

## Architektur: Backend-Typ + Adapter-Pattern

Vorbild: bestehendes Adapter-Pattern in `communication/base.py`
(Protocol/ABC + konkrete Adapter je Backend) und die **Ollama-Provider-UX**
(Provider mit `api_base` in `llm.json`, GUI-konfigurierbar).

### VideoBackend-Protocol (core)

```python
class VideoBackend(Protocol):
    async def list_models(provider: dict) -> list[MediaModel]: ...
    async def submit(provider, model, prompt, params, image_url=None) -> JobRef: ...
    async def poll(provider, job: JobRef) -> JobStatus: ...   # pending|done|error + output-ref
    async def fetch_output(provider, job) -> bytes|Path: ...  # Roh-Output holen
```

Konkrete Adapter:
- `OpenRouterVideoBackend` — bestehender Code, refactored hinter das Protocol.
- `ComfyUIVideoBackend` — `POST /prompt` (Workflow-Graph mit Platzhaltern),
  `GET /history/{id}` (poll), `GET /view?...` (WebP/FLAC holen) →
  ffmpeg-Konvertierung zu MP4 (die Kette existiert schon im media_workspace).
- `SwitchHttpVideoBackend` — spricht den node-lokalen Switch-Wrapper auf
  Muskeln2 (submit/poll/fetch), der intern Ollama↔sd-server umschaltet. Der
  Wrapper (Kunde/Mia) kapselt die VRAM-Orchestrierung + sicheren Vulkan-Flags.
  (Ein direkter `SdServerVideoBackend` ohne Wrapper wäre nur sinnvoll, wenn
  sd-server dauerhaft liefe — hier NICHT der Fall wegen VRAM-Konflikt mit Ollama.)

### Config in llm.json (GUI-verwaltet)

Neuer Provider-Typ neben den LLM-Providern — Wiederverwendung der
Ollama-`api_base`-Mechanik:

```json
{
  "media_backends": [
    {
      "id": "muskeln1-comfy",
      "type": "comfyui",
      "name": "Muskeln1 ComfyUI (LTX-2.3)",
      "api_base": "http://192.168.1.78:8189",
      "workflows": [
        {
          "id": "ltx-t2v",
          "label": "LTX-2.3 Text→Video",
          "category": "video",
          "output_node": "SaveAnimatedWEBP",
          "graph": { /* ComfyUI API-Format JSON */ },
          "placeholders": {
            "prompt": "6.inputs.text",
            "seed": "3.inputs.seed",
            "width": "...", "height": "...", "frames": "..."
          },
          "durations": [5, 10], "aspect_ratios": ["16:9","9:16"],
          "frame_images": ["first_frame"]
        },
        {
          "id": "sdxl-image",
          "label": "SDXL Text→Bild",
          "category": "image",
          "output_node": "SaveImage",
          "graph": { /* ComfyUI API-Format JSON */ },
          "placeholders": { "prompt": "...", "seed": "...", "width": "...", "height": "..." }
        }
      ]
    },
    {
      "id": "muskeln2-sd",
      "type": "switch-http",
      "name": "Muskeln2 (RealVisXL / LTX-GGUF, On-Demand-Switch)",
      "api_base": "http://muskeln2:9700",
      "note": "Wrapper schaltet Ollama<->sd-server; Modelle via GET /models live"
    }
  ]
}
```

Modell-ID-Schema im Dialog: `local:<provider_id>/<workflow_or_model_id>`
(analog zu `ollama/…`). So bleiben lokale und OpenRouter-Modelle unterscheidbar
und im selben Dropdown mischbar.

## Muskeln2 (.81): VRAM-Konflikt & On-Demand-Switch (Modus 2 + Option A)

**Entschieden (till + Kunde/Mia, 2026-07-25):** Muskeln2 fährt im Alltag **Ollama**
(Sprachmodell). Bild/Video über sd-server ist nur möglich, wenn Ollama **entladen**
ist — VRAM ist ein Nullsummenspiel (Radeon VII 16GB + RX 470 8GB, ~30GB RAM,
`--offload-to-cpu` = System-Freeze). Beides gleichzeitig = OOM/Crash.

Deshalb: **KEIN permanenter sd-server-Service.** Stattdessen ein **node-lokaler
Switch-Wrapper** (Option A), der die Umschaltung kapselt:

```
Kill/Unload Ollama → Start sd-server (sichere Vulkan-Flags) → Wait ready
  → Generate → Fetch result → Kill sd-server → Ollama lädt wieder
```

### Warum node-lokal (nicht HydraHive orchestriert das direkt)
Die sicheren Flags sind fragil und hardware-spezifisch:
`--auto-fit --max-vram vulkan0=15,vulkan1=7 --vae-tiling`, **niemals**
`--offload-to-cpu`. Dieses Wissen bleibt auf der Node — ein Fehler übers Netz
würde die Kundenmaschine einfrieren. HydraHive sendet nur „mach Bild/Video",
der Wrapper weiß, wie er *seine* GPUs sicher bedient.

### Aufgabenteilung
- **Kunde/Mia baut** den node-lokalen Wrapper auf Muskeln2 (kennt die sicheren
  Flags am besten). Klein (~HTTP-Dienst), hält Ollama↔sd-server-Umschaltung.
- **HydraHive baut** den generischen `switch-http`-Adapter, der gegen die unten
  definierte API spricht — egal was dahinter steckt.

### Wrapper-API-Vertrag (HydraHive spricht GENAU das an)
Der Wrapper läuft dauerhaft (leichtgewichtig, kein VRAM), Default z.B.
`http://muskeln2:9700`:

| Endpoint | Zweck | Antwort |
|----------|-------|---------|
| `GET  /health` | lebt der Wrapper? aktueller Modus | `{"status":"ok","mode":"ollama\|sd\|switching"}` |
| `GET  /models` | verfügbare sd-Modelle/Presets | `[{"id","name","category":"image\|video"}]` |
| `POST /generate` | Job starten (kapselt Ollama-Unload + sd-server-Start) | `{"job_id"}` |
| `GET  /status/{job_id}` | pollen | `{"state":"pending\|running\|done\|error","message?"}` |
| `GET  /result/{job_id}` | Ergebnis holen (MP4/PNG bytes oder URL) | binär oder `{"url"}` |
| `POST /release` (optional) | sd-server beenden, zurück zu Ollama | `{"ok":true}` |

`POST /generate` Payload:
```json
{ "model": "realvisxl-image", "category": "image|video",
  "prompt": "...", "seed": 123, "width": 768, "height": 432,
  "frames": 121, "image_url": "data:...optional (I2V)" }
```

Der Wrapper garantiert: Nach `done`/`error` (oder Timeout) schaltet er sd-server
ab und lässt Ollama wieder laden. HydraHive muss sich **nicht** um VRAM kümmern.

### Wichtig: sd-server hat KEINE Workflows (anders als ComfyUI)

Klarstellung von Mia (2026-07-25): sd-server (stable-diffusion.cpp) ist **kein**
Node-Graph-System. Es gibt **keine** Workflow-JSONs/Graphen wie bei ComfyUI —
nur eine **direkte REST-API** (Prompt + Parameter → Bild/Video). Das
Workflow-Template-Konzept (Graph + placeholders) gilt **ausschließlich für
ComfyUI (Muskeln1)**.

Für Muskeln2 gilt: Der node-lokale **Switch-Wrapper** kapselt den sd-server-
Aufruf (inkl. sicherer Vulkan-Flags). HydraHive spricht nur den Wrapper-Vertrag
unten — das interne sd-server-Payload-Schema kennt nur der Wrapper. Mia liefert
das echte sd-server-Payload-Schema (`prompt`, `steps`, `width`, `height` …), das
der Wrapper intern nutzt; HydraHive muss es NICHT kennen.

### Adapter `switch-http` (HydraHive-Seite)
- Config: `{ "type":"switch-http", "api_base":"http://muskeln2:9700" }`
- `list_models` → `GET /models`; `submit` → `POST /generate`;
  `poll` → `GET /status/{id}`; `fetch_output` → `GET /result/{id}`.
- „Verbindung testen" → `GET /health` (zeigt auch den aktuellen `mode`).
- **Unterschied zu ComfyUI/OpenRouter:** Ein Generate kann Minuten dauern
  (inkl. Modell-Switch). UI zeigt „schalte um / generiere …" mit dem `mode`.

### Netzwerk-Erreichbarkeit (Mias Hinweis, Modus-2-tauglich)
- **NUR der Wrapper** (`:9700`) läuft permanent und muss erreichbar sein —
  sd-server (`:8080`) startet der Wrapper selbst on-demand, ist von außen egal.
- Empfehlung: `muskeln2` in `/etc/hosts` der Master-Node (oder mDNS
  `muskeln2.local`), damit die Config einen stabilen Hostnamen nutzt statt IP.
- Kein Reverse-Proxy nötig für v1 (Direktzugriff Master → Wrapper reicht).

## GUI (alles über die Oberfläche — harte Anforderung)

### 1. Media-Backend-Verwaltung (Admin/Cockpit → LLM/Media-Bereich)
- **Backend hinzufügen**: Typ wählen (ComfyUI / sd-server), Name, `api_base`.
- **„Verbindung testen"**-Button: pingt `/object_info` (ComfyUI) bzw. den
  sd-server-Health-Endpoint → grün/rot + erkannte Version.
- **ComfyUI — Workflow hinzufügen** (das Herz von Option A, komplett GUI):
  - Workflow-JSON (API-Format) per **Textfeld einfügen ODER Datei-Upload**.
  - HydraHive parst den Graphen, listet die Nodes/Felder und lässt den User
    per Dropdown die **Platzhalter mappen** (welches Feld = Prompt, Seed,
    Breite, Höhe, Frames, Startbild). Vorschläge automatisch (Heuristik:
    CLIPTextEncode→prompt, EmptyLatentVideo→frames/w/h, KSampler→seed).
    → Kein manuelles JSON-Editieren nötig.
  - Label + Kategorie (video/image) + Dauer-/Seitenverhältnis-Optionen setzen.
- **sd-server**: Modelle werden (wenn die API es hergibt) live gelistet; sonst
  trägt der User Modell-Namen + Default-Flags (`--vae-tiling`, `--auto-fit …`)
  als Preset im UI ein.

### 2. Video-Dialog (Atelier)
- Modell-Dropdown zeigt **gruppiert**: „OpenRouter", „Muskeln1 (ComfyUI)",
  „Muskeln2 (sd-server)".
- Dauer/Seitenverhältnis/Startbild-Felder respektieren die Metadaten des
  gewählten lokalen Modells (z.B. LTX max ~257 Frames / 768×432 als Grenzen).

## Backend-Flow (submit→poll→convert→save)

1. Dialog schickt `model="local:muskeln1-comfy/ltx-t2v"` + prompt/params.
2. Router erkennt `local:`-Prefix → wählt Adapter über `type` des Providers.
3. **ComfyUI**: nimmt das Workflow-`graph`, ersetzt Platzhalter (prompt/seed/
   frames/w/h/image), `POST /prompt` → `prompt_id`; poll `GET /history/{id}`;
   Output (WebP-Frames [+FLAC]) via `GET /view` holen → ffmpeg → MP4 in
   `generated/`. (ffmpeg-Kette existiert bereits in `media_workspace`.)
4. **sd-server**: submit an dessen HTTP-API, poll, MP4/PNG holen, speichern.
5. Ergebnis landet wie heute in der Atelier-Galerie/Timeline.

## Sicherheit

- `api_base` ist frei wählbar → SSRF-Fläche (wie beim Ollama-Provider bewusst
  akzeptiert; Media-Backend anzulegen ist eine Admin-/privilegierte Aktion).
- Workflow-JSON wird nur an das konfigurierte ComfyUI geschickt, nicht
  ausgeführt in HydraHive. Größenlimit + JSON-Schema-Validierung beim Upload.
- Timeouts + Job-Abbruch (lange Video-Renders).

## Akzeptanzkriterien

1. Admin kann in der GUI ein ComfyUI-Backend anlegen, „Verbindung testen" ist grün.
2. Admin kann per GUI einen LTX-Workflow (API-JSON) hinzufügen und die
   Platzhalter mappen — ohne JSON-Handarbeit.
3. Admin kann ein sd-server-Backend anlegen (IP+Port, „Verbindung testen" grün).
4. Der Atelier-Video-Dialog zeigt lokale Modelle gruppiert neben OpenRouter.
5. Ein T2V-Job über ComfyUI-LTX läuft durch: submit→poll→ffmpeg→MP4 in Galerie.
6. OpenRouter-Pfad bleibt unverändert (Regression-Schutz, Tests grün).
7. Kein konfiguriertes Backend / Backend offline → sauberer Fehler, kein Crash,
   OpenRouter-Modelle weiterhin wählbar.

## Umsetzungs-Etappen (jede mit Tests, klein & mergebar)

- **E1** ✅ (PR #375): `media_backends`-Config + `VideoBackend`-Protocol + OpenRouter
  refactored dahinter (keine Verhaltensänderung, reine Struktur).
- **E2** ✅ (PR #376): `ComfyUIVideoBackend` (submit/poll/view + ffmpeg) +
  Workflow-Template-Modell.
- **E3** ✅ (PR #377): GUI — Media-Backend-Verwaltung + „Verbindung testen" +
  Workflow-Upload/Mapping.
- **E4** ✅: `SwitchHttpVideoBackend` (Adapter gegen den Wrapper-API-Vertrag),
  in `_ADAPTERS` registriert. Gegen einen Mock des Vertrags getestet (25 Tests),
  blockiert also **nicht** auf Mias Wrapper. GUI-Preset + Test-Endpoint waren
  bereits aus E3 vorhanden. Offen bleibt nur der Live-Test gegen den echten
  Wrapper (→ E6).
- **E5**: Video-Dialog: gruppiertes Dropdown + lokale Metadaten/Limits.
- **E6**: Doku (`docs/local-video-backends.md`) + Live-Test beim Kunden.

## Offene Punkte / Risiken

- **Switch-Wrapper wird vom Kunden/Mia gebaut** gegen den oben definierten
  API-Vertrag. HydraHive-Adapter kann gegen einen Mock des Vertrags entwickelt+
  getestet werden — echter End-to-End-Test erst mit fertigem Wrapper. Der
  interne sd-server-CLI-Aufruf (sichere Vulkan-Flags) ist Sache des Wrappers,
  NICHT von HydraHive.
- **ComfyUI UI→API-Format**: v1 verlangt API-Format vom User (Save API Format).
  Konverter optional als Folge-Feature.
- **Job-Dauer**: Video-Renders dauern Minuten → async Job-Handling + Timeouts.
