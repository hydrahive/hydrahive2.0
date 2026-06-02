# Feature Map: Samba — SMB-Shares

> **Modul:** `core/src/hydrahive/samba/`  
> **Konfiguration:** `/etc/samba/hh-projects.d/`  
> **Was:** SMB-Shares auf Projekt-Workspaces. Datei-Zugriff vom Windows/Mac-Netzwerk.  
> **Warum:** Bequemer Datei-Transfer — kein SFTP, kein SCP, einfach Netzlaufwerk.

---

## Wie es funktioniert

```
Projekt aktiviert Samba:
  POST /api/projects/{id}/samba
    → samba/manager.py schreibt Config-Datei
    → /etc/samba/hh-projects.d/<project-id>.conf
    → smbcontrol smbd reload
    → Share sofort verfügbar

Windows-Client:
  \\homelab\projektname
  → smbd authenticiert via Samba-User-DB
  → Zugriff auf /var/lib/hydrahive2/workspaces/projects/<id>/
```

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `samba/manager.py` | Share erstellen/löschen. Config-Dateien schreiben. `smbcontrol`-Aufrufe. |
| `samba/config_template.py` | Jinja2-Template für Samba-Config-Dateien |
| `samba/users.py` | Samba-User-Verwaltung (smbpasswd-Integration) |
| `api/routes/samba.py` | REST-Endpoints |

---

## Config-Template

```ini
# /etc/samba/hh-projects.d/<project-id>.conf

[projektname]
   path = /var/lib/hydrahive2/workspaces/projects/<id>
   valid users = till, bibi
   read only = no
   browseable = yes
   create mask = 0644
   directory mask = 0755
   comment = HydraHive: Projektname
```

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `POST /api/projects/{id}/samba` | Share aktivieren |
| `DELETE /api/projects/{id}/samba` | Share deaktivieren |
| `GET /api/samba/users` | Samba-User auflisten |
| `POST /api/samba/users` | Samba-User anlegen / Passwort setzen |
| `DELETE /api/samba/users/{name}` | Samba-User entfernen |

---

## Samba-User vs HH2-User

Samba nutzt eigene Passwort-DB (smbpasswd), nicht die HH2-User-DB.
`samba/users.py` synchronisiert: wenn HH2-User Samba-Zugriff aktiviert → `smbpasswd -a username`.

---

## Verwandte Subsysteme

- **→ Projects** (`15-projects.md`): Samba ist Feature von Projekten
- **→ Auth** (`21-auth-security.md`): Samba-User-Sync
