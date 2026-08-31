# Ollama-Modellmanager

## Ziel

Der bestehende LLM-Modellkatalog verwaltet in der ersten Ausbaustufe ausschließlich Ollama-Modelle. Administratoren können Modelle der offiziellen Ollama Library finden, ihre Eignung für den aktuellen Rechner beurteilen, lokale Details und Fähigkeiten sehen sowie Modelle installieren und entfernen.

Andere lokale Backends, Hugging-Face-/GGUF-Importe und Mediengeneratoren sind nicht Bestandteil dieser Ausbaustufe. Das Frontend-Datenmodell bleibt um weitere Backends erweiterbar.

## Quellen und Vertrauensgrenzen

HydraHive verbindet drei getrennte Quellen:

1. **Offizielle Ollama Library (`https://ollama.com/library`)**
   - Familien, Beschreibungen, deklarierte Fähigkeiten und Tags.
   - Die Liste wird serverseitig mit kurzer Laufzeitbegrenzung und Cache geladen.
   - Bei Ausfall bleibt die lokale Modellverwaltung benutzbar.
2. **Konfigurierter Ollama-Endpunkt**
   - `/api/tags`: installierte Modelle, Digests, Größen und Quantisierung.
   - `/api/show`: Kontextfenster und deklarierte Fähigkeiten.
   - `/api/pull`: Installation mit NDJSON-Fortschritt.
   - `/api/delete`: Entfernung.
   - Der Client verwendet ausschließlich die administrativ konfigurierte `api_base`; Request-Daten dürfen keine Ziel-URL liefern.
3. **llmfit**
   - Liefert Hardwaredaten, Fit-Level, Laufmodus, Speicherbedarf und geschätzte beziehungsweise gemessene Tokenrate.
   - HydraHive führt den Prozess ohne Shell und mit fester Argumentliste sowie Timeout aus.
   - Wenn llmfit fehlt oder ein Modell nicht zugeordnet werden kann, bleibt der Katalog funktionsfähig und kennzeichnet den Fit als nicht verfügbar.
   - llmfit bewertet den HydraHive-Host. Liegt der konfigurierte Ollama-Endpunkt nicht auf Loopback, zeigt HydraHive bewusst keinen Fit an, statt die Hardware des falschen Rechners zuzuordnen.

## API

Alle Endpunkte sind Admin-only.

### `GET /api/llm/catalog/ollama`

Liefert:

- Verbindungszustand und konfigurierte, redigierte Basis-URL
- erkannte Hardware aus llmfit, soweit verfügbar
- offizielle Modellfamilien
- installierte lokale Modelle
- laufende Pull-Jobs

Installierte Modelle werden über den Ollama-Namen zusammengeführt. Nicht installierte Familien erscheinen mit ihrem Standardtag `latest`; konkrete Varianten werden lazy geladen.

### `GET /api/llm/catalog/ollama/library/{family}`

Liefert die offiziellen Tags einer Modellfamilie einschließlich Downloadgröße, Kontext und Eingabeart, soweit die Ollama Library diese Daten veröffentlicht.

`family` wird strikt validiert. Erlaubt sind nur Kleinbuchstaben, Ziffern sowie `.`, `_` und `-`.

### `POST /api/llm/catalog/ollama/pulls`

Body:

```json
{"model":"qwen3:14b"}
```

Startet höchstens einen Pull pro Modell. Der Endpunkt antwortet sofort mit einer Job-ID. Modellnamen werden strikt validiert; HydraHive übergibt sie als JSON und niemals an eine Shell.

### `GET /api/llm/catalog/ollama/pulls/{job_id}`

Liefert Status, aktuelle Phase, Gesamtbytes, abgeschlossene Bytes und einen sicheren Fehlercode. Interne Stacktraces oder Ollama-Response-Bodies werden nicht zurückgegeben.

### `DELETE /api/llm/catalog/ollama/models/{model}`

Entfernt ein installiertes Modell nur, wenn es nicht als globales Standard-, Embedding-, Medien-, Provider- oder Agentenmodell referenziert wird. Die Antwort nennt bei Konflikt ausschließlich verständliche Referenzbezeichnungen.

## Datenmodell

Eine Modellzeile enthält mindestens:

- `id`: HydraHive-ID (`ollama/<name>`)
- `ollama_name`: nativer Ollama-Name
- `installed`, `size`, `digest`, `modified_at`
- `family`, `parameter_size`, `quantization`
- `context_window`
- `capabilities`: maschinenlesbare Liste, z. B. `completion`, `tools`, `thinking`, `vision`, `embedding`
- `input_modalities`, `output_modalities`
- `fit`: `perfect`, `good`, `marginal`, `too_tight` oder `unknown`
- `memory_required_gb`, `memory_available_gb`
- `estimated_tps`, `measured_tps`, `estimate_confidence`
- `run_mode`, `best_quant`, `score`

Deklarierte Ollama-Fähigkeiten sind keine Verifikation. Das Schema reserviert deshalb `capability_verification`; in dieser Ausbaustufe werden vorhandene echte Tests angezeigt, neue automatische Vision-/Tool-Testläufe sind nicht Teil der Installationsaktion.

## Pull-Zustandsmaschine

```text
queued -> pulling -> success
                  -> failed
```

Der Jobfortschritt ist pro Prozess verfügbar. Ein Serverneustart beendet laufende Jobs; beim nächsten Katalogaufruf bestimmt `/api/tags` den tatsächlichen Installationszustand neu. Die API behauptet keine Restart-Persistenz.

## Fehlerverhalten

- Ollama offline: HTTP 200 beim Katalog mit `connected=false`; Mutationen antworten mit einem codierten 503-Fehler.
- Offizielle Library offline: lokale Modelle bleiben sichtbar; `library_error` wird gesetzt.
- llmfit fehlt/Timeout/ungültiges JSON: `hardware_fit.available=false`; kein Katalogausfall.
- Doppelte Pull-Anfrage: bestehender aktiver Job wird idempotent zurückgegeben.
- Delete eines nicht installierten Modells: codierter 404-Fehler.
- Delete eines referenzierten Modells: HTTP 409 mit Referenzliste.

## Sicherheit

- Sämtliche Verwaltungsendpunkte benötigen `require_admin`.
- Keine frei wählbaren URLs in Requests; damit kein neuer SSRF-Vektor.
- Keine Shell-Ausführung mit Modellnamen.
- Strikte Modell-/Familiennamenvalidierung und Längenbegrenzung.
- Externe Requests haben Timeouts, Redirects sind deaktiviert und Antwortgrößen werden begrenzt beziehungsweise gestreamt.
- Fehlermeldungen enthalten keine Secrets, internen Pfade oder vollständigen Upstream-Antworten.
- Löschen prüft Referenzen vor dem Upstream-Aufruf.

## Nicht enthalten

- ComfyUI, Bild-, Musik-, Video- oder TTS-Modellverwaltung
- beliebige Hugging-Face-/GGUF-Imports
- Ollama-Cloud-Konten
- automatische Entfernung referenzierter Modelle
- persistente Pull-Jobs über Serverneustarts
- automatische Capability-Benchmarks für jedes neu installierte Modell
