# Feature Map: Containers — LXC/Docker

> **Modul:** `core/src/hydrahive/containers/`  
> **Frontend:** `frontend/src/features/containers/`  
> **Was:** Container-Management (LXC und/oder Docker). Lifecycle, Stats, Logs, Console.  
> **Warum:** Extensions laufen in Containern. Agents können Container verwalten.

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/containers` | Alle Container |
| `POST /api/containers` | Container erstellen |
| `GET /api/containers/{id}` | Container-Details |
| `PUT /api/containers/{id}` | Config ändern |
| `DELETE /api/containers/{id}` | Container löschen |
| `POST /api/containers/{id}/start` | Starten |
| `POST /api/containers/{id}/stop` | Stoppen |
| `POST /api/containers/{id}/restart` | Neustart |
| `GET /api/containers/{id}/stats` | CPU/RAM/Netzwerk-Stats |
| `GET /api/containers/{id}/logs` | Container-Logs |
| `GET /api/containers/{id}/console` | WebSocket-Console (Shell) |

---

## Frontend-Dateien

| Datei | Verantwortung |
|---|---|
| `ContainersPage.tsx` | Übersicht aller Container mit Status-Badges |
| `ContainerDetailPage.tsx` | Detail-Ansicht: Tabs für Config, Stats, Logs, Console |
| `ContainerCard.tsx` | Container-Karte in der Übersicht |
| `ContainerConfigPane.tsx` | Config-Tab |
| `ContainerStatsPane.tsx` | Stats-Tab (Live-Graphen) |
| `ContainerLogPane.tsx` | Log-Tab |
| `ConsolePane.tsx` | Console-Tab (Terminal im Browser) |
| `ContainerConsoleModal.tsx` | Console als Modal |
| `CreateContainerDialog.tsx` | Dialog: neuen Container erstellen |
| `EditContainerDialog.tsx` | Dialog: Container bearbeiten |
| `StatusBadge.tsx` | Farbiger Status-Badge (running/stopped/error) |

---

## Verwandte Subsysteme

- **→ Extensions** (`25-extensions.md`): Extensions nutzen Container
- **→ API** (`04-api.md`): `routes/containers_*.py`
