# Feature Map: Projects — Workspaces, Git, Samba

> **Modul:** `core/src/hydrahive/projects/`  
> **Datenpfad:** `/var/lib/hydrahive2/projects/<project-id>/`  
> **Was:** Projekte sind isolierte Arbeitsräume mit eigenem Dateisystem, Git-Repo, Agent.  
> **Warum:** Trennung von Aufgaben — "Bibliothek" != "Arztpraxis" != "Claude Import".

---

## Was ist ein Projekt?

Ein Projekt besteht aus:
1. **Metadata** (Name, Beschreibung, Members, Status)
2. **Workspace** (`/var/lib/hydrahive2/workspaces/projects/<id>/`) — Dateisystem
3. **Project-Agent** (optional, automatisch) — KI-Assistent für dieses Projekt
4. **Git-Repo** (optional) — Versionskontrolle im Workspace
5. **Samba-Share** (optional) — SMB-Zugriff auf Workspace
6. **Allowed-Specialists** — welche Specialist-Agents darf das Projekt nutzen

---

## Projekt-Lifecycle

```
POST /api/projects
  → Projekt-Record in DB
  → Workspace-Verzeichnis anlegen
  → (Optional) Project-Agent anlegen
  → (Optional) Git-Init
  → (Optional) Samba-Share aktivieren

Projekt aktiv:
  → Agents arbeiten im Workspace
  → Git-Commits via shell_exec oder projects_git_ops
  → Dateien via file_read/file_write im Workspace-Scope

DELETE /api/projects/{id}
  → Soft-Delete oder Hard-Delete
  → Optional: Workspace löschen
  → Optional: Agent löschen
```

---

## Workspace-Struktur

```
/var/lib/hydrahive2/workspaces/projects/<project-id>/
├── <Projektdateien...>          # Arbeitsdateien des Projekts
├── .git/                        # Git-Repo (wenn aktiviert)
└── .hh2/                        # HH2-interne Metadaten
    └── project.json
```

**Pfad-Sicherheit:** Agents können nur innerhalb ihres Workspace arbeiten.
`tools/_path.py` verhindert Ausbrüche (z.B. `../../etc/passwd`).

---

## Git-Integration

| Endpoint | Beschreibung |
|---|---|
| `GET /api/projects/{id}/git/status` | `git status` im Workspace |
| `GET /api/projects/{id}/git/log` | Commit-History |
| `GET /api/projects/{id}/git/branches` | Branch-Liste |
| `GET /api/projects/{id}/git/diff` | Diff |
| `POST /api/projects/{id}/git/commit` | Commit erstellen |
| `POST /api/projects/{id}/git/push` | Push zu Remote |
| `POST /api/projects/{id}/git/pull` | Pull von Remote |
| `POST /api/projects/{id}/git/checkout` | Branch wechseln |
| `POST /api/projects/{id}/git/init` | Repo initialisieren |

**Remote-Repos:** SSH-Key oder HTTPS-Credentials aus Credential-Store.

---

## Samba-Integration

```python
# Samba-Share aktivieren:
POST /api/projects/{id}/samba
  → Schreibt Config nach /etc/samba/hh-projects.d/<project-id>.conf
  → Reload smbd

# Samba-Share deaktivieren:
DELETE /api/projects/{id}/samba
```

**Share-Name:** automatisch aus Projekt-Name generiert.
**Zugriff:** Samba-User aus HH2-User-DB, Passwort aus User-Config.
**Path:** direkt auf Workspace-Verzeichnis.

---

## Members & Berechtigungen

```json
{
  "members": ["admin", "till", "bibi"],
  "allowed_specialists": [
    {"id": "uuid", "name": "ISBN Extractor"}
  ]
}
```

- **Members**: Können Projekt sehen und bearbeiten
- **Allowed Specialists**: Welche Specialist-Agents darf das Projekt nutzen
- **Owner**: Member der das Projekt angelegt hat

---

## Vorhandene Projekte

| Projekt | ID | Beschreibung |
|---|---|---|
| Bibliothek | 019e1e35... | E-Book-Sammlung |
| Arztpraxis | 019e2e42... | Medizinische Dokumente |
| Claude Import | 019e3301... | Claude-Chat-Import |
| (intern) | 019dfa2d... | System-intern |
| (intern) | 019e3845... | System-intern |

---

## Frontend

`frontend/src/features/projects/` — Projekt-Verwaltungs-UI:
- Projekt-Liste mit Status
- Workspace-Datei-Browser
- Git-Panel (Status, Log, Commit, Push)
- Samba-Toggle
- Members verwalten

---

## Verwandte Subsysteme

- **→ Agents** (`05-agents.md`): Project-Agents sind an Projekte gebunden
- **→ Samba** (`28-samba.md`): Samba-Share-Verwaltung
- **→ Tools** (`02-tools.md`): `list_projects` gibt Projekt-Liste zurück
- **→ API** (`04-api.md`): Alle routes/projects_*.py
