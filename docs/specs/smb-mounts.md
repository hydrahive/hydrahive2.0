# SMB-Mounts — Fileserver-Freigaben als Projekt-Ressource

## Was
Ein User kann **SMB/CIFS-Freigaben auf fremden Fileservern** (NAS, Backup-Server)
als Ressource in HydraHive anlegen und einem Projekt zuweisen — analog zum
bestehenden „Server zuweisen"-Flow (VMs/Container). Das zugewiesene Share wird
per `mount.cifs` in den Projekt-Workspace gemountet, sodass der Agent es als
ganz normalen Ordner sieht (lesen/schreiben → z.B. Backups ablegen).

## Warum
- Heute existiert nur das **umgekehrte** Feature (`projects_samba.py`):
  HydraHive *exportiert* den eigenen Projekt-Workspace als SMB-Share.
- Gefordert ist der Client-Fall: eine **externe** Freigabe einbinden.
- Use-Case: Projekt bekommt eine Backup-Freigabe auf dem Fileserver.

## Abgrenzung — NICHT Teil dieser Phase
- Kein SMB-Browser/Discovery (Shares manuell per Hand eintragen).
- Kein Auto-Reconnect-Daemon (Phase 2). Mount bei Assign, umount bei Unassign.
- Kein NFS (nur CIFS/SMB).

## Bestehende Patterns (wird 1:1 gespiegelt)
| Aspekt              | Vorlage                                              |
|---------------------|------------------------------------------------------|
| Modell (Dataclass)  | `vms/models.py::VM`                                   |
| DB-Schicht          | `vms/db.py` (create/get/list/delete/set_project/…)   |
| Migration           | `db/migrations/0NN_*.sql` (numeriert, auto-applied)  |
| project_id-Muster   | `005_project_assignments.sql` (NULLable, kein CASCADE)|
| Assign-Routes       | `api/routes/projects_servers.py`                     |
| Credentials         | `credentials/store.py`, Typ `basic` (user/password)  |
| sudo-Subprocess     | `samba/manager.py::_reload_smbd` (Vorbild)           |
| Workspace-Pfad      | `projects/_paths.py::workspace_path(project_id)`     |

## Datenmodell

### Dataclass `SmbMount` (`core/src/hydrahive/smbmounts/models.py`)
```
mount_id      str   (uuid7, PK)
owner         str   (username)
name          str   (1-32, ^[a-zA-Z][a-zA-Z0-9_-]{0,31}$ — wird Mount-Ordnername)
host          str   (Hostname/IP des Fileservers)
share         str   (Share-Name, z.B. "backups")
subpath       str|None  (optionaler Unterpfad innerhalb des Shares)
credential    str|None  (Name eines 'basic'-Credentials des Owners; None = guest)
read_only     bool  (default False)
options       str|None  (zusätzliche mount-Optionen, whitelist-validiert)
project_id    str|None  (zugewiesenes Projekt)
mount_state   Literal["unmounted","mounting","mounted","error"]
last_error_code  str|None
created_at / updated_at  str
```

### Migration `030_smb_mounts.sql`
```sql
CREATE TABLE smb_mounts (
    mount_id        TEXT PRIMARY KEY,
    owner           TEXT NOT NULL,
    name            TEXT NOT NULL,
    host            TEXT NOT NULL,
    share           TEXT NOT NULL,
    subpath         TEXT,
    credential      TEXT,
    read_only       INTEGER NOT NULL DEFAULT 0,
    options         TEXT,
    project_id      TEXT,
    mount_state     TEXT NOT NULL DEFAULT 'unmounted',
    last_error_code TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX idx_smb_mounts_project ON smb_mounts(project_id);
CREATE INDEX idx_smb_mounts_owner   ON smb_mounts(owner);
```

## Mount-Mechanik (`core/src/hydrahive/smbmounts/mounter.py`)
- Mountpoint = `workspace_path(project_id) / "mounts" / name`
  → Agent sieht das Share unter `mounts/<name>/` im Workspace.
- Credential-Auflösung: `credentials.store.get_credential(owner, cred_name)` →
  user/password aus einem `basic`-Eintrag. Passwort wird **niemals** als
  Klartext in der DB oder in der Prozess-Cmdline übergeben.
- CIFS-Auth über **Credentials-File** (`mount -t cifs -o credentials=<tmpfile>`),
  Datei chmod 600, im Mount-Namespace, nach mount gelöscht. NICHT als
  `-o username=…,password=…` (würde in `ps`/`/proc` sichtbar).
- Aufruf via `sudo mount.cifs` (sudoers-Whitelist, Vorbild `_reload_smbd`).
  umount analog via `sudo umount`.
- Optionen-Whitelist: nur `uid,gid,file_mode,dir_mode,vers,ro,rw,iocharset`
  werden durchgereicht; alles andere wird verworfen (kein Injection-Vektor).

## API (`core/src/hydrahive/api/routes/smbmounts.py` + Erweiterung projects)
Eigene CRUD-Routes für die Ressource (wie VMs „gehören dem User"):
```
GET    /api/smb-mounts                 → eigene Mounts auflisten
POST   /api/smb-mounts                 → anlegen
GET    /api/smb-mounts/{id}            → Detail
PATCH  /api/smb-mounts/{id}            → ändern (nur wenn unmounted)
DELETE /api/smb-mounts/{id}            → löschen (vorher unmount)
POST   /api/smb-mounts/{id}/test       → Verbindung testen (mount+umount probe)
```
Projekt-Zuweisung (spiegelt `projects_servers.py`):
```
GET    /api/projects/{pid}/mounts            → zugewiesene Mounts
GET    /api/projects/{pid}/mounts/available  → freie (project_id IS NULL, owner=user)
POST   /api/projects/{pid}/mounts/assign     → zuweisen + mounten
DELETE /api/projects/{pid}/mounts/{id}       → unassign + umount
```
- Beim **Projekt-Löschen**: `clear_project_assignments(project_id)` +
  vorher alle zugehörigen Mounts umounten (Hook in den Projekt-Delete-Pfad).
- Audit: `project_audit.log(project_id, user, "mount_assigned"/"mount_unassigned")`.

## Sicherheit
- Nur `basic`-Credentials des **eigenen** Owners referenzierbar.
- `host`/`share`/`subpath`/`name` strikt validiert (kein Shell-Metachar, kein
  `..`, kein Whitespace in host/share).
- `mount.cifs` + `umount` über eng gefasste sudoers-Regel (nur diese zwei
  Binaries, nur in Mountpoints unterhalb von `data_dir/workspaces/…/mounts/`).
- Mountpoint-Pfad serverseitig konstruiert, nie aus User-Input → kein
  Path-Traversal.
- Credentials-File: tmpfile mit chmod 600, sofort nach mount entfernt.

## Akzeptanzkriterien
1. User kann unter „SMB-Freigaben" einen Mount anlegen (host/share/cred).
2. „Verbindung testen" gibt klares OK/Fehler (probe mount+umount).
3. Mount lässt sich einem Projekt zuweisen → erscheint als `mounts/<name>/`
   im Agent-Workspace, lesbar **und** schreibbar (sofern nicht read_only).
4. Agent kann darin Dateien anlegen (Backup-Use-Case) → landet auf dem
   Fileserver.
5. Unassign / Projekt-Löschen → sauberer umount, kein verwaister Mount.
6. Passwort taucht **nirgends** in DB, Logs, `ps` oder `/proc/*/cmdline` auf.
7. Alle neuen Dateien ≤ ~200 Zeilen, keine `print()`, Settings über Singleton.

## Offene Punkte (Phase 2)
- Auto-Remount nach Reboot / Verbindungsverlust (Reconciler wie bei VMs).
- Frontend-UI (diese Spec ist Backend-first; UI danach).
- Mount-Health/Stats im Dashboard.
```
```
