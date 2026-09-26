# LLM-Katalog V2 — Multi-Node-Modellkatalog und Capability-Verifikation

## Status

Designentscheidung bestätigt: Der Katalog wird **allgemein für viele Nutzer und mehrere Ausführungs-Nodes** entworfen. Die vorhandene Workstation `192.168.178.197` ist nur der erste Pilot und darf keine Sonderlogik erhalten.

Dieses Dokument erweitert `ollama-model-manager.md`. Der bestehende Ollama-Katalog bleibt kompatibel; V2 ergänzt Nodes, echte Capability-Verifikation und reproduzierbare Benchmarks.

## Ziel

Der LLM-Katalog soll nicht nur Modellnamen und Herstellerangaben anzeigen, sondern pro Modell und Ausführungs-Node belastbar beantworten:

- Ist das Modell installiert oder verfügbar?
- Auf welcher Hardware und welchem Node kann es laufen?
- Welche Fähigkeiten sind nur deklariert und welche wurden tatsächlich verifiziert?
- Welche Geschwindigkeit und welcher Speicherbedarf wurden real gemessen?
- Darf der aktuelle Benutzer beziehungsweise das aktuelle Projekt dieses Modell verwenden?
- Kann ein Administrator das Modell sicher installieren, aktualisieren oder entfernen?

## Architekturentscheidung: Node statt Host-Sonderfall

Ein **Node** ist die Ausführungsumgebung, auf der ein lokaler Modellserver und/oder ein Hardware-Adapter läuft. Der Core darf nicht annehmen, dass seine eigene Hardware die Modell-Hardware ist.

```text
HydraHive Core
  └── Node Registry
        ├── Core-Node
        ├── Ollama-Node (lokal oder remote)
        ├── später: Media-Node / Workstation-Agent
        └── später: weitere Modellserver
```

Ein Provider verweist auf einen Node. Hardware-Fit, Benchmark und Modell-Lifecycle werden immer dem Node zugeordnet, der die Anfrage tatsächlich ausführt.

Die Workstation `192.168.178.197` wird als normaler `ollama`-Node konfiguriert. Es gibt keine IP-spezifische Ausnahme.

## Node-Datenmodell

Ein Node benötigt mindestens:

```json
{
  "id": "node-uuid",
  "name": "Till Workstation",
  "kind": "ollama",
  "endpoint": "server-side-reference",
  "status": "online",
  "shared": true,
  "owner_user_id": null,
  "capabilities": ["chat", "tools", "vision", "embedding"],
  "hardware": {
    "cpu": "...",
    "gpu": "...",
    "gpu_vram_gb": 16,
    "available_vram_gb": 12.4
  },
  "hardware_source": "llmfit",
  "last_seen_at": "..."
}
```

Sicherheitsregeln:

- Die tatsächliche Endpoint-URL bleibt serverseitig und wird nicht aus einem freien Frontend-Request übernommen.
- Node-Anlage und Endpoint-Änderung sind Admin-Aktionen.
- `shared=true` bedeutet für alle berechtigten Nutzer verwendbar; private Nodes bekommen eine Owner-/Projektprüfung.
- Ein Modell darf nur verwendet werden, wenn User- und Projektberechtigungen des Nodes erfüllt sind.
- Direkte Browserzugriffe auf Ollama bleiben verboten.

## Provider- und Modellzuordnung

Ein Modell ist nicht nur durch seine ID eindeutig. Der vollständige Schlüssel lautet:

```text
(node_id, provider_id, model_name, model_digest)
```

Dadurch werden gleiche Modellnamen auf unterschiedlichen Nodes getrennt bewertet. Ein Ollama-Pull auf Node A darf nicht den Installationsstatus auf Node B verändern.

## Capability-Vertrag

Ollama-/Provider-Metadaten gelten als **Deklaration**, nicht als Beweis.

Jede Fähigkeit erhält einen separaten Status:

```json
{
  "tools": {
    "declared": true,
    "status": "verified",
    "verified_at": "...",
    "probe_version": 1,
    "details": "native tool call and HydraHive dispatch succeeded"
  },
  "vision": {
    "declared": true,
    "status": "declared"
  }
}
```

Erlaubte Statuswerte:

- `verified` — reproduzierbarer Probe erfolgreich
- `failed` — Probe reproduzierbar fehlgeschlagen
- `declared` — Provider behauptet die Fähigkeit, noch nicht getestet
- `unknown` — keine belastbare Aussage
- `not_supported` — explizit nicht verfügbar

V1 der Probes:

- `chat`: kurze deterministische Antwort
- `tools`: echter Function-/Tool-Call an ein ungefährliches internes Probe-Tool
- `embedding`: Vektor wird erzeugt und Dimension geprüft
- `vision`: expliziter Bild-Probejob, nur wenn ein Testbild und ein kompatibler Node vorhanden sind
- `audio`: später als eigener Probe-Typ
- `image`, `video`, `music`: nicht fälschlich aus Ollama-Chat-Fähigkeiten ableiten; diese bleiben backend-spezifisch

Die Tool-Probe darf niemals reale Benutzer-Tools, Shell-Befehle, Mail, Dateien oder Netzwerkziele ausführen. Sie verwendet ein internes No-op-/Echo-Tool und prüft den vollständigen Weg:

```text
Catalog Probe → LiteLLM/Provider → native tool_call → Probe-Dispatcher → Ergebnis
```

Probe-Ergebnisse werden nach `model_digest`, `node_id` und `probe_version` gecacht. Ein Modell-Update invalidiert die alten Ergebnisse.

## Benchmark-Vertrag

Benchmarks laufen als Hintergrundjobs und blockieren keine Katalogseite.

Mindestens zu erfassen:

- Node und Modell-Digest
- Probe-/Benchmark-Version
- Start-/Endzeit
- Prompt-Tokens
- Output-Tokens
- Prompt-Tokens pro Sekunde
- Output-Tokens pro Sekunde
- Ladezeit und Antwortzeit getrennt
- VRAM vor/nach dem Lauf, soweit der Node dies liefert
- Fehlercode statt interner Fehlermeldung

Ein einzelner Wall-Clock-Wert darf nicht mehr als Geschwindigkeit ausgegeben werden.

Benchmarks dürfen nicht automatisch bei jedem Seitenaufruf und nicht automatisch nach jedem Pull gestartet werden. Installation und Verifikation sind getrennte, bestätigungspflichtige Aktionen.

## Hardware-Fit

Der Fit wird auf dem jeweiligen Modell-Node berechnet:

- lokaler Ollama-Node: lokales `llmfit` oder gleichwertiger Adapter
- Remote-Ollama-Node: Node-Agent/llmfit-Service auf dem Remote-System
- fehlender Adapter: `fit=unknown`, kein Fit vom HydraHive-Core erben

Der Katalog muss Quelle und Zeitpunkt anzeigen:

```text
Fit: gut
Quelle: Till Workstation / llmfit
Gemessen: 2026-09-18 19:00
```

## API-Richtung

Bestehende Ollama-Endpunkte bleiben zunächst kompatibel. V2 ergänzt eine nodebezogene Form:

```text
GET  /api/llm/nodes
POST /api/llm/nodes                 (Admin)
PATCH /api/llm/nodes/{node_id}      (Admin)
DELETE /api/llm/nodes/{node_id}     (Admin, Referenzschutz)
GET  /api/llm/catalog?node_id=...
POST /api/llm/catalog/probes        (Admin oder berechtigter Nutzer)
GET  /api/llm/catalog/probes/{job_id}
POST /api/llm/catalog/benchmarks    (Admin oder berechtigter Nutzer)
GET  /api/llm/catalog/benchmarks/{job_id}
```

Pull/Delete bleiben backend-spezifisch, werden aber über `node_id` adressiert:

```text
POST   /api/llm/nodes/{node_id}/ollama/pulls
DELETE /api/llm/nodes/{node_id}/ollama/models/{model}
```

Freie URLs, freie Provider-IDs und freie Shell-Argumente aus dem Browser sind nicht erlaubt.

## Frontend-Richtung

Der Katalog erhält:

- Node-Auswahl mit Online-/Offline-Status
- Filter nach Modalität, Capability-Status, Fit und Installation
- deklarierte und verifizierte Fähigkeiten getrennt
- Benchmark-/Probe-Aktionen mit Fortschritt
- Geschwindigkeit als Prompt-/Output-tok/s
- Hardware- und Datenquellen-Hinweis
- Installieren, Aktualisieren und Entfernen pro Node
- klare Warnung, wenn ein Modell nur deklariert, aber nicht verifiziert ist

Ein Modell darf nur dann als Agentenmodell angeboten werden, wenn es auf dem ausgewählten Node installiert und für Chat verifiziert oder ausdrücklich als unbekannt bestätigt wurde. Tool-Agenten benötigen zusätzlich eine erfolgreiche Tool-Probe.

## Implementierungsreihenfolge

1. Node-/Scope-Datenmodell und serverseitige Provider-Zuordnung
2. Capability- und Probe-Vertrag inklusive sicherem No-op-Tool
3. Hintergrundjob für Tool-/Chat-Probes
4. Benchmarkjob mit tok/s und Modell-Digest
5. Remote-Hardware-Adapter/Node-Agent-Vertrag
6. Ollama-Pull/Delete auf `node_id` umstellen
7. Frontend auf Node-, Probe- und Benchmarkdaten erweitern
8. Migration und Kompatibilität für den bestehenden Single-Ollama-Provider

## Abnahmekriterien

- Zwei Ollama-Nodes mit gleichem Modellnamen werden unabhängig angezeigt und bewertet.
- Ein Remote-Node erhält niemals fälschlich den Hardware-Fit des Core-Hosts.
- Ein deklarierter Tool-Support wird nicht als verifiziert angezeigt.
- Eine erfolgreiche Tool-Probe enthält einen echten nativen Tool-Call und Dispatcher-Erfolg.
- Probe und Benchmark laufen als Jobs und überleben Browser-Reconnects.
- Pull/Delete sind nodebezogen, admin-geschützt und referenzsicher.
- Ein Nutzer sieht nur freigegebene Nodes und Modelle.
- Bestehende Cloud-Provider und die bisherige Agentenmodellwahl bleiben kompatibel.
