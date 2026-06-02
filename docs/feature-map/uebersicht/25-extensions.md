# Feature Map: Extensions — Erweiterbare Fähigkeiten

> **Modul:** `core/src/hydrahive/extensions/`  
> **Frontend:** `frontend/src/features/extensions/`  
> **Was:** Dynamisch installierbare Erweiterungen. Laufen in isolierten Containern.  
> **Warum:** HH2 ist erweiterbar ohne Core zu ändern. Community-Extensions möglich.

---

## Konzept

Extensions sind wie "Apps" für HydraHive:
- Eigener Prozess (Container oder Python-Venv)
- Registriert sich beim HH2-Core via API
- Kann Tools, Webhooks, UI-Panels beisteuern
- Eigene Settings und Credentials

---

## Extension-Manifest

```json
{
  "id": "my-extension",
  "name": "My Extension",
  "version": "1.0.0",
  "description": "Macht tolle Sachen",
  "author": "till",
  "tools": [
    {
      "name": "my_tool",
      "description": "...",
      "parameters": {...}
    }
  ],
  "webhooks": ["/api/extensions/my-extension/webhook"],
  "ui_panels": ["/api/extensions/my-extension/ui"],
  "settings_schema": {...}
}
```

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/extensions` | Alle Extensions |
| `POST /api/extensions` | Extension installieren |
| `GET /api/extensions/{id}` | Extension-Details |
| `PUT /api/extensions/{id}` | Config ändern |
| `DELETE /api/extensions/{id}` | Extension deinstallieren |
| `POST /api/extensions/{id}/enable` | Aktivieren |
| `POST /api/extensions/{id}/disable` | Deaktivieren |
| `POST /api/extensions/{id}/restart` | Neustart |
| `GET /api/extensions/{id}/logs` | Extension-Logs |
| `GET /api/extensions/{id}/tools` | Tool-Schema der Extension |
| `POST /api/extensions/{id}/settings` | Settings speichern |

---

## Tool-Integration

Wenn eine Extension Tools registriert:
- Tools bekommen Präfix `ext__<extension-id>__<tool-name>`
- Dispatcher erkennt `ext__`-Präfix
- Tool-Call wird an Extension-Container weitergeleitet
- Analog zu MCP-Tools (`mcp__`-Präfix)

---

## Verwandte Subsysteme

- **→ MCP** (`13-mcp.md`): ähnliches Konzept, anderes Protokoll
- **→ Plugins** (`10-plugins.md`): Plugins sind einfacher (Python, kein Container)
- **→ Containers** (`24-containers.md`): Extensions laufen in Containern
- **→ Tools** (`02-tools.md`): `ext__`-Tools kommen via Extensions
