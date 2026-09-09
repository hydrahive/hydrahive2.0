# AI-Sicherheit

HydraHive-Modul für einen optionalen, lokal betriebenen [Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard).

## MVP-Grenze

Der aktuelle MVP unterstützt ausschließlich AI-Infrastruktur-Scans. MCP-, Skill-, Agent- und Jailbreak-Scans sind absichtlich noch nicht aktiviert. Insbesondere werden keine beliebigen Quellcodearchive hochgeladen und keine aktiven Red-Team-Prompts ausgeführt.

## Konfiguration

```bash
export HH_AI_SECURITY_AIG_URL=http://127.0.0.1:8088
export HH_AI_SECURITY_TARGETS=http://127.0.0.1:11434,http://127.0.0.1:8000
```

`HH_AI_SECURITY_TARGETS` ist eine exakte Origin-Allowlist. Ein Ziel mit anderem Port, Pfad, Query, Fragment oder Zugangsdaten wird abgelehnt. Ohne Allowlist sind keine Ziele scanbar.

Der AIG-Webserver darf nicht öffentlich gebunden werden. Die Upstream-Compose-Datei muss vor einem produktiven Einsatz insbesondere auf Container-Rechte, Netzwerkzugriff und fehlende Authentifizierung geprüft werden. Das HydraHive-Modul aktiviert keinen privilegierten Docker-Service automatisch.

## Cockpit

Das Modul registriert `/ai-security` im Infrastrukturbereich des HydraHive-Cockpits. Die Seite ist auf Administratoren beschränkt und zeigt Runtime-Erreichbarkeit, die konfigurierte Ziel-Allowlist, laufende Scans und redigierte Reports. Bei fehlender Runtime bleibt das Modul read-only und zeigt den Zustand statt Fehlerdetails aus dem Upstream weiterzugeben.

Die Runtime wird absichtlich nicht automatisch gestartet. HydraHive spricht einen separat betriebenen AI-Infra-Guard über `HH_AI_SECURITY_AIG_URL` an; Docker-in-Docker und Docker-Socket-Mounts sind nicht Teil des Moduls.

## API

Alle Endpunkte benötigen HydraHive-Authentifizierung und liegen unter `/api/modules/ai-security`:

- `GET /health`
- `GET /targets`
- `GET /scans`
- `POST /scans` mit `{ "scan_type": "infra", "target_url": "..." }`
- `GET /scans/{id}`

Ergebnisse werden benutzerbezogen gespeichert, auf Größe begrenzt und vor Speicherung um typische Geheimnisfelder redigiert.

## Attribution

Die Integration basiert auf Tencent Zhuque Lab AI-Infra-Guard. Bei Weitergabe müssen die Upstream-[Apache-2.0-Lizenz](https://github.com/Tencent/AI-Infra-Guard/blob/main/LICENSE) und [NOTICE](https://github.com/Tencent/AI-Infra-Guard/blob/main/NOTICE) berücksichtigt werden.
