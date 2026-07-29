# Spec: Projekt-Member-Rechte (Read / Write / Admin)

**Issue:** #75 · **Branch:** `feat/project-member-roles` · **Stand:** 2026-07-29

## Was
Projekt-Mitgliedschaft wird von binär (`members: list[str]`) auf rollenbasiert
umgestellt: jeder Member hat eine Rolle `read | write | admin`. Die Rollen
werden serverseitig pro Operation durchgesetzt.

## Warum
Bei mehreren Personen pro Projekt braucht man Abstufung: ein Junior darf
Sessions öffnen/mitlesen, aber nicht Settings ändern oder Members verwalten.

## Datenmodell (die eine maßgebliche Quelle)
`config.json` → `members: list[{username: str, role: 'read'|'write'|'admin'}]`

- Bleibt im File (konsistent mit allen anderen Projekt-Feldern), **keine** DB.
- `created_by` ist implizit **admin** (steht nicht zwingend in `members`).
- Default-Rolle beim Hinzufügen: `write`.

### Backward-Compat (verbindlich)
`_normalize()` migriert beim **Lesen** transparent:
- `members: ["till", "bibs"]` → `[{"username":"till","role":"write"}, {"username":"bibs","role":"write"}]`
- gemischte Listen (teils str, teils dict) werden ebenfalls normalisiert.
- Alte Configs werden dadurch beim nächsten Save automatisch aufs neue Format
  gehoben — kein separater Migrationslauf nötig.

## Abstraktionsschicht (Kern der „sauberen" Lösung)
Neues Modul `projects/_members_model.py` (oder Funktionen in bestehendem
`members.py`) mit:

- `role_of(project: dict, username: str) -> str | None`
  - `created_by` → `"admin"`
  - sonst Rolle aus `members`, oder `None` wenn kein Member
- `usernames(project: dict) -> list[str]` — reine Namensliste (ersetzt alle
  bisherigen `p.get("members", [])`-Iterationen)
- `ROLE_RANK = {"read":1, "write":2, "admin":3}` + `has_at_least(role, required)`

**Regel:** Niemand außer diesem Modul greift direkt auf die members-Struktur zu.
Alle ~10 heutigen `username in members`-Stellen rufen `usernames()` bzw.
`role_of()` auf.

## Enforcement
`check_project_access(project, username, role, required='read')` in
`_project_route_helpers.py`:
- System-Admin (`role == "admin"` aus Auth) → immer erlaubt
- sonst: `has_at_least(role_of(project, username), required)`
- kein Zugriff → `403 project_no_access`

### Rollen-Matrix (Default; beim Review kippbar)
| Operation | benötigt |
|---|---|
| Projekt sehen, Dateien lesen, Session öffnen/mitlesen, Read-Tools | read |
| Session starten, Workspace/Dateien schreiben, Skills anlegen | write |
| Members verwalten, Settings ändern, Projekt löschen | admin |

## Betroffene Stellen (alle auf Abstraktion umstellen)
- `projects/_config_io.py` — `_normalize` (Migration), `list_for_user` (via `usernames`)
- `projects/config.py` — `create`, `update` (validate), `delete` (affected_users via `usernames`)
- `projects/members.py` — `add(project, username, role='write')`, `remove`, neu `set_role`
- `projects/_validation.py` — `validate_members` akzeptiert dict-Form + Rolle
- `api/routes/_project_route_helpers.py` — `check_project_access(required=...)`, Pydantic-Modelle
- `api/routes/projects.py` — Member-Routen (add mit role, set_role-Endpoint)
- `api/routes/sessions.py` — `_assert_project_access` (start→write, open→read)
- `api/routes/projects_files*.py` — read→read, write→write
- `api/routes/skills.py` — `_check_project_access` (write für Anlegen)
- `api/routes/butler.py`, `_git_helpers.py`, `projects_samba.py`,
  `_server_route_helpers.py` — via `usernames()`
- `tools/list_projects.py` — `members` weiterhin ausgeben (Namen + Rolle)
- `agents/_workspace_links.py` — `usernames()` statt direktem members-Zugriff

## Frontend
- `frontend/src/features/projects/…` — Member-Liste zeigt Rolle, Rollen-Dropdown
  (nur für admin/created_by editierbar), Hinzufügen mit Rollenwahl.
- API-Typen anpassen (`members: {username, role}[]`).

## Akzeptanzkriterien
1. Alte Config (`members: list[str]`) lädt fehlerfrei, alle Member als `write`.
2. `read`-Member kann Session **öffnen/mitlesen**, aber **nicht starten** (403).
3. `read`/`write`-Member kann **keine** Members verwalten/Settings ändern (403).
4. `admin`-Member + `created_by` können Members verwalten.
5. System-Admin darf weiterhin alles.
6. Kein direkter members-Struktur-Zugriff außerhalb `_members_model` (grep-Check).
7. pytest grün (inkl. neuer Rollen-Tests), ruff grün, tsc/eslint grün.

## Nicht in v1
- Rollenvererbung, Custom-Rollen, per-Tool-Granularität, DB-Auslagerung.
