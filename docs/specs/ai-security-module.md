# Spec: AI-Security-Modul mit AI-Infra-Guard

## Ziel

HydraHive erhält ein optional installierbares Modul `ai-security`, das einen lokal oder intern betriebenen Tencent AI-Infra-Guard sicher anbindet. Das Modul stellt eine authentifizierte HydraHive-Oberfläche für AI-Infrastruktur-Scans bereit und speichert Scanstatus sowie Ergebnisse benutzerbezogen.

Der HydraHive-Core bleibt unabhängig vom Scanner. AI-Infra-Guard wird nicht als Python-Code in den Core importiert, sondern als separater Dienst beziehungsweise als später separat prüfbarer CLI-Provider betrieben.

## Verifizierte Upstream-Grundlage

- Repository: <https://github.com/Tencent/AI-Infra-Guard>
- Lizenz: Apache-2.0; `NOTICE` mit verpflichtender Attribution bleibt bei jeder Integration erhalten.
- Upstream-Task-API:
  - `POST /api/v1/app/taskapi/tasks`
  - `GET /api/v1/app/taskapi/status/{id}`
  - `GET /api/v1/app/taskapi/result/{id}`
- Upstream weist selbst darauf hin, dass der Dienst nicht öffentlich betrieben werden soll.
- Der offizielle Compose-Agent benötigt privilegierte Container-Rechte. Diese werden im ersten MVP nicht automatisch erweitert oder ungeprüft aktiviert.

## MVP-Grenze

### Im MVP enthalten

1. Modulmanifest und Backend-Adapter.
2. Authentifizierter Health-Check des konfigurierten AIG-Dienstes.
3. Konfigurierbare, exakt erlaubte AI-Service-Ziele.
4. AI-Infra-Scan als einziger aktivierbarer Scan-Typ.
5. Persistente Scan-Datensätze mit Benutzerbindung.
6. Polling des Upstream-Status über einen überwachten Moduljob.
7. Speicherung des Upstream-Ergebnisses als JSON mit Größenlimit.
8. API-Fehler- und Timeout-Behandlung ohne interne Details in Responses.
9. Tests für Authentifizierung, Ziel-Allowlist, User-Isolation, Upstream-Fehler und Statusübergänge.

### Nicht im MVP enthalten

- MCP- und Skill-Scan.
- Agent-Scan und Jailbreak-Evaluation.
- Upload beliebiger Dateien oder Quellcodearchive.
- Freie Ziel-URLs aus dem Browser.
- automatische Behebung von Findings.
- öffentliche Erreichbarkeit des AIG-Dienstes.
- Installation eines privilegierten Docker-Agenten ohne explizite spätere Freigabe.
- direkte Speicherung oder Weitergabe von Modell-API-Keys durch das Frontend.

## Sicherheitsmodell

### HydraHive-API

Alle Modul-Endpunkte verwenden `require_auth`. Ein Benutzer darf nur eigene Scans lesen und abrufen. Die externe AIG-Session-ID ist kein alleiniger Zugriffsschlüssel.

### Ziel-Allowlist

AI-Infra-Ziele werden ausschließlich aus `HH_AI_SECURITY_TARGETS` gelesen. Die Variable enthält eine komma-separierte Liste vollständiger Origins, zum Beispiel:

```text
http://127.0.0.1:11434,http://127.0.0.1:8000
```

Ein Scan akzeptiert nur einen exakt passenden Origin inklusive Scheme, Host und Port. Pfade, Userinfo, Query und Fragment sind verboten. Nicht konfigurierte Ziele werden mit `target_not_allowed` abgewiesen. Es gibt keinen allgemeinen URL-Fetcher und keinen frei übergebenen Custom-Header im MVP.

Die Allowlist ist eine ausdrückliche Betreiberfreigabe für lokale/interne Dienste und darf deshalb nicht durch den allgemeinen Outbound-SSRF-Block ersetzt werden. Trotzdem werden URL-Schema, Host-Form und Port strikt validiert.

### Upstream-Verbindung

Die AIG-Basis-URL kommt aus `HH_AI_SECURITY_AIG_URL` und darf standardmäßig nur auf Loopback zeigen. HydraHive spricht ausschließlich den konfigurierten Upstream an. AIG-Fehler, Response-Größen und Timeouts werden begrenzt.

### Daten

- Scaninhalt und Ergebnisse sind benutzergebunden.
- Upstream-Response wird auf maximal 2 MiB begrenzt.
- Fehlertexte werden gekürzt und enthalten keine Tokens, Header oder vollständige Upstream-Responses.
- `model.token`, `api_key`, `Authorization` und vergleichbare Felder werden vor Speicherung redigiert, falls sie trotzdem vom Upstream geliefert werden.
- Ergebnisse werden nicht automatisch in Agentenkontexte oder Memory übernommen.

## Datenmodell

Tabelle `module_ai_security_scans`:

- `id` — lokale UUID
- `username` — Eigentümer
- `scan_type` — im MVP nur `infra`
- `target_url` — erlaubter Origin ohne Credentials
- `upstream_session_id` — AIG-Session-ID, nullable
- `status` — `queued`, `running`, `completed`, `failed`
- `result_json` — redigierter JSON-Report, nullable
- `error_code` — stabile interne Fehlerklasse, nullable
- `created_at`, `updated_at`, `completed_at`

Indizes auf `(username, created_at)` und `(status, updated_at)`.

## API

Prefix: `/api/modules/ai-security`.

- `GET /health`
  - authentifiziert
  - meldet `configured`, `reachable` und eine nicht-sensitive Fehlklasse
- `GET /targets`
  - authentifiziert
  - liefert nur die konfigurierten Origins
- `GET /scans`
  - authentifiziert
  - nur Scans des aktuellen Benutzers
- `POST /scans`
  - authentifiziert
  - Body: `{ "scan_type": "infra", "target_url": "http://127.0.0.1:11434" }`
  - startet einen Upstream-Task und liefert HTTP 202
- `GET /scans/{scan_id}`
  - authentifiziert und eigentümergeprüft
  - liefert Status und, bei Abschluss, den redigierten Report

## Moduljob

`ctx.register_job("poll_scans", ...)` fragt fällige `queued`/`running`-Scans in begrenzter Zahl ab. Jeder Tick:

1. liest höchstens 20 aktive Datensätze,
2. fragt Status beim Upstream ab,
3. setzt `running`, `completed` oder `failed`,
4. lädt bei `completed` genau einmal das Ergebnis,
5. isoliert jeden Fehler pro Scan.

Der Job verwendet keine freien User-URLs, sondern nur die bereits gespeicherte und bei Erstellung validierte Ziel-URL. Bei AIG-Unerreichbarkeit bleibt ein Scan zunächst `running`; nach einem begrenzten Timeout wird er `failed`.

## Konfiguration

| Variable | Standard | Bedeutung |
|---|---:|---|
| `HH_AI_SECURITY_AIG_URL` | `http://127.0.0.1:8088` | interner AIG-Webserver |
| `HH_AI_SECURITY_TARGETS` | leer | exakt erlaubte Ziel-Origin-Liste |
| `HH_AI_SECURITY_HTTP_TIMEOUT` | `10` | Connect-/Read-Timeout in Sekunden |
| `HH_AI_SECURITY_MAX_RESULT_BYTES` | `2097152` | maximale Reportgröße |

Die Konfiguration wird über das HydraHive-Settings-Singleton gelesen. Secrets werden nicht als Modulkonfiguration eingeführt.

## Späterer Ausbau

### MCP-/Skill-Scan

Eigene Upload- und Workspace-Pfade müssen vorab mit einer sicheren Pfad-Allowlist, Archivbomben-Schutz, Größenlimit und Sandbox-Strategie spezifiziert werden. Keine freie Upload-Weitergabe an einen privilegierten Upstream-Agenten.

### Agent-/Jailbreak-Evaluation

Nur separat opt-in, mit Zielbesitz-Bestätigung, Kosten-/Request-Limit, Audit-Event und deutlicher Kennzeichnung als aktiver Red-Team-Test.

### Service-Installation

Erst nach einem Test auf einem isolierten Host. Die Installation muss Container-Rechte, Datenverzeichnisse, Bind-Adresse, Firewall und Rollback explizit prüfen. Ein Upstream-Compose mit `SYS_ADMIN`/`seccomp:unconfined` darf nicht blind Bestandteil der normalen Modulinstallation werden.

## Akzeptanzkriterien

- [ ] Modul wird ohne AIG-Dienst ladbar; Health zeigt `configured=false` beziehungsweise `reachable=false`.
- [ ] Unauthentifizierte Requests werden abgewiesen.
- [ ] Nur exakt konfigurierte Origins können gescannt werden.
- [ ] Jeder Scan ist nur für seinen Eigentümer sichtbar.
- [ ] Upstream-Task wird mit `type=ai_infra_scan` und genau einem erlaubten Ziel erstellt.
- [ ] AIG-Status `completed` lädt einen redigierten Report; `failed` wird als stabiler Fehlerstatus gespeichert.
- [ ] Upstream-Timeout oder ungültige Antwort blockiert weder API noch Polling anderer Scans.
- [ ] Response- und Reportgrößen sind begrenzt.
- [ ] MCP, Skill, Agent und Jailbreak sind im MVP nicht versehentlich erreichbar.
- [ ] Bestehende Core- und Modul-Tests bleiben grün.

## Attribution

Bei Auslieferung des Moduls müssen `LICENSE`/`NOTICE` des Upstreams berücksichtigt und in Modul-Dokumentation oder About-Ansicht auf Tencent Zhuque Lab AI-Infra-Guard sowie das Originalrepository verwiesen werden.
