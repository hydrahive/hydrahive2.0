# Spec: Local Media Runtime

Status: APPROVED
Datum: 2026-09-05
Pilot: `tills-master-wks` (RTX 5060 Ti, 16 GiB VRAM)

## Was

Lokale Bild- und Videogenerierung wird als optionale GPU-Extension betrieben. HydraHive Core enthält nur die leichtgewichtige Backend-Registry und das Job-Routing; Atelier bleibt die kreative Oberfläche. Auf einem ausgewählten GPU-Node läuft ein authentifizierter HydraHive Media Worker vor einer ausschließlich lokal gebundenen ComfyUI-Instanz.

## Warum

Installationen ohne GPU dürfen keine CUDA-/ROCm-Pakete, Modelle oder Generierungsdienste erhalten. Gleichzeitig kann die GPU auf einer Workstation oder einem Compute-Node statt auf dem HydraHive-Server liegen. Die Trennung hält den Core klein und erlaubt mehrere spezialisierte Generierungsnodes.

## Architektur

```text
Atelier / Agent-Tools
        |
HydraHive Media-Backend-Registry
        |
gekoppelter, authentifizierter Media Worker auf GPU-Node
        |
ComfyUI auf localhost
        |
Bild-/Video-Workflows und Modelle
```

### Verantwortungen

- **Core:** Modellkatalog, Standardmodelle, Job-Routing, Ergebnisübertragung und Backend-Konfiguration.
- **Atelier-Modul:** Prompting, Charaktere, Galerie, Videojobs, Timeline und Filmexport.
- **Local Media Runtime Extension:** GPU-Abhängigkeiten, Worker, ComfyUI, Modelle, Workflows, Prozess-/VRAM-Steuerung.

### Verhalten ohne GPU/Extension

- keine Runtime-Installation und keine Modelldownloads,
- keine lokalen Modelle im Katalog,
- Cloud-Backends bleiben unverändert nutzbar,
- Admin kann auf einem geeigneten Node bewusst die Einrichtung starten.

## Media-Worker-Vertrag

Der Worker ist die einzige Netzwerkgrenze. ComfyUI bindet ausschließlich an localhost.

- `GET /health`
- `GET /capabilities`
- `GET /models`
- `GET /workflows`
- `POST /jobs`
- `GET /jobs/{id}`
- `DELETE /jobs/{id}`
- `GET /jobs/{id}/result`

Jeder Endpoint verlangt eine node-gebundene, widerrufbare Authentifizierung. Jobs und Resultate sind an Node, HydraHive-Instanz und Job-ID gebunden.

## Sicherheit

- keine frei erreichbare ComfyUI-API im LAN,
- keine ungeprüften Ziel-URLs pro Job,
- `api_base` wird aus gekoppelten Nodes erzeugt, nicht aus Generierungsrequests,
- Modell- und Workflow-IDs müssen aus dem Worker-Katalog stammen,
- Größenlimits für Workflow, Prompt, Referenzbilder und Ergebnisse,
- Pfad-Traversal verhindern; Dateinamen nie ungeprüft übernehmen,
- begrenzte Parallelität, Timeouts, Abbruch und Cleanup,
- keine Shell-Interpolation mit Modell-/Workflow-/Promptwerten,
- Modelle werden nur nach Größen-/Lizenzbestätigung heruntergeladen,
- Credentials nie in Logs, URLs oder Frontendantworten.

## VRAM-Modi

- `parallel`: Ollama und ComfyUI dürfen gleichzeitig geladen bleiben.
- `auto-release`: Ollama vor Media-Job entladen, ComfyUI ausführen, danach GPU freigeben.
- `media-only`: Node ausschließlich für Bild/Video.

Der Pilot startet mit `parallel`; erst Messwerte dürfen einen Wechsel auf `auto-release` auslösen.

## Pilot-Fakten

Read-only geprüft am 2026-09-05:

- Host: `tills-master-wks`
- GPU: NVIDIA GeForce RTX 5060 Ti
- VRAM: 16.311 MiB
- NVIDIA-Treiber: 595.84
- Docker vorhanden
- ComfyUI noch nicht installiert/als User-Service registriert
- freier Speicher: ca. 399 GiB

## Installation und Updates

Auf GPU-Nodes erfolgt die Einrichtung automatisch durch die Installations- und
Updatepfade. `installer/modules/72-local-media.sh` (Server-Installation) und
`node-agent/scripts/setup-local-media.sh` (Compute-Node) erkennen NVIDIA, sorgen
für Docker und das signierte NVIDIA Container Toolkit, testen `--gpus all`,
laden das gepinnte ComfyUI-Image und starten es ausschließlich auf
`127.0.0.1:8188`. Auf Nodes ohne NVIDIA-GPU wird die Extension ohne Fehler
übersprungen. Es gibt keine erforderliche manuelle Nachinstallation.

### Umsetzung

### P1: Routing vervollständigen

- gemeinsamer lokaler Media-Job-Runner für `image|video`,
- lokale Standardmodelle in `generate_image` und `generate_video`,
- Atelier-Bild- und Videojobs über dieselbe Core-Registry,
- Resultate in bestehende Galerie-/Video-Stores.

### P2: Optionale Extension

- Media Worker und authentifizierter Node-Vertrag,
- ComfyUI nur localhost,
- explizite Extension-Installation statt Core-Abhängigkeit.

### P3: Geführte Node-Installation

- GPU-Erkennung,
- Profile Bild/Video/beides,
- Modellgröße und Lizenz bestätigen,
- automatische Backend-Registrierung.

### P4: WKS-Pilot

- Bildworkflow,
- Text-to-Video und Image-to-Video,
- E2E bis Galerie/Timeline,
- VRAM-Messung neben Ollama.

## Akzeptanzkriterien

- Eine Installation ohne GPU bleibt unverändert und lädt keine Runtime-Artefakte.
- Ein Admin kann gezielt einen geeigneten GPU-Node erweitern.
- Lokale Modelle erscheinen nur bei erreichbarer, gekoppelter Runtime.
- Standard-Bild- und Standard-Videomodell können `local:`-IDs verwenden.
- Agent-Tools und Atelier routen dieselbe lokale Modell-ID identisch.
- Bildresultate landen in der Galerie, Videoresultate im Video-Store/Timeline.
- Worker-Ausfall erzeugt einen verständlichen Jobfehler und keinen Cloud-Fallback.
- Cloud-Pfade bleiben regressionsfrei.
