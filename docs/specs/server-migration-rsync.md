# Server-Migration: Voll-Klon per rsync (Server-zu-Server)

Status: DESIGN (freigegeben durch Till, 2026-07-01)
Issue: TBD

## Problem

Umzug einer kompletten HydraHive2-Installation auf einen neuen Server (z.B. den
"121er") als **100%-Klon inkl. ALLER Daten** — ausdrücklich auch der großen
Rohdaten (894 GB Plattenarchive im Archivierungs-Projekt, VMs, Mounts). Das
vorhandene tar.gz-System-Backup ist dafür ungeeignet:

- 8-GiB-Extraktions-Limit (Dekompressionsbomben-Schutz)
- HTTP-Download eines Monolithen — bei 1,2 TB nicht praktikabel
- übergeht ohnehin `workspaces/` + `modules/` (separater Bug, eigener Task)

HydraHive **1** hatte eine Migration-Page (Ziel-Adresse + SSH-Key eingeben →
Server-zu-Server-Transfer mit Live-Log). Technisch war es aber `tar | openssl |
ssh` (Streaming) und übertrug nur `/agents/` + `/etc/hydrahive/` (wenige hundert
MB). Ein tar-Stream über 1,2 TB ist nicht wiederaufnehmbar — bricht die
Verbindung ab, fängt alles von vorn an.

## Ziel

Gewohnter HH1-Ablauf, aber mit rsync statt tar-Stream:
Am **alten** Server: Migration-Seite → Ziel-Adresse + SSH-Zugang eingeben →
"Klonen" → Live-Fortschritt → auf dem neuen Server steht ein 100%-Klon.

## Gewählter Ansatz: rsync-Push über SSH (Option A)

Warum rsync statt tar-Stream:
- **inkrementell + resumierbar** — bei 1,2 TB der Unterschied zwischen "läuft
  durch" und "bricht immer wieder komplett ab". Zweiter Lauf überträgt nur das
  Delta.
- **erhält alles** mit `-aAX`: Permissions, Ownership, Timestamps, ACLs, xattrs,
  Symlinks → echter Klon
- Standardwerkzeug, auf beiden Linux-Servern vorhanden (rsync 3.2.7 verifiziert)

### Architektur (HH2-konform)

**Privilegierter Pfad — kein sudo im Core-Service.** Der Core-Service läuft als
User `hydrahive` (ProtectHome=read-only) und kann root-owned `vms/` nicht lesen.
Deshalb dasselbe Muster wie Self-Update/Restart:

1. **Core-Router** (`/api/admin/migration/*`, admin-only) validiert die Eingaben
   und schreibt eine Trigger-Datei `.migration_request` (JSON: target, ssh_port,
   include-Optionen) nach `data_dir`. **Keine** Ausführung im Core-Service.
2. **systemd-path-Watcher** (`hydrahive2-migration.path`) triggert
   `hydrahive2-migration.service` (oneshot, **User=root**), analog zu
   `hydrahive2-update`. Der führt `installer/migrate.sh` aus.
3. **`migrate.sh`** (root) macht:
   - Preflight: SSH-Erreichbarkeit, rsync auf Ziel vorhanden, HH2 auf Ziel
     installiert, freier Plattenplatz auf Ziel >= Quell-Datenmenge
   - konsistenter DB-Snapshot via `sqlite3 .backup` (WAL-safe) in Temp
   - `rsync -aAX --delete --info=progress2` je Datenbereich über SSH
   - Ziel-Services vor DB-Sync stoppen, danach starten (Restart-Trigger auf Ziel)
   - Ownership/Permissions auf Ziel korrigieren (chown hydrahive, /etc 640 etc.)
   - Log nach `/var/log/hydrahive2-migration.log`
4. **Live-Log**: Frontend pollt/streamt `/api/admin/migration/log` (SSE), das die
   Logdatei tailt — wie beim Update-Log. Status via `.migration_request`-Existenz
   + Exit-Marker.

### Was wird übertragen (VOLL-Klon — Till: "ich brauche alle Daten")

Alle Daten-Wurzeln, jeweils mit `rsync -aAX`:

| Quelle | Inhalt |
|---|---|
| `/var/lib/hydrahive2/` | agents, projects, **workspaces** (inkl. 894 GB Archive), modules, plugins, credentials, users, whatsapp, generated, exports, mail, skills, scratchpad, vms, sessions.db (als Snapshot) |
| `/etc/hydrahive2/` | Configs, Secrets (jwt, internal), llm.json, users.json, api_keys, extensions |
| `/var/log/hydrahive2-*.log` | optional |

**Excludes** (regenerierbarer Ballast — NICHT Nutzdaten):
`node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `.mypy_cache/`,
`.pytest_cache/`, `.plugin-cache/`, `.module-cache/`, `.numba-cache/`,
`gocache/`, `gomods/`, `.backup-rollback-*`, `.hh2-restore-*`,
`memory_index.db` (BM25-Index, wird neu gebaut), `.git/` NICHT excluden (Till
braucht die Git-Repos!).

Live-`sessions.db` wird durch den `.backup`-Snapshot ersetzt (nicht das offene
WAL-File syncen).

### Sicherheit
- admin-only (require_admin)
- SSH StrictHostKeyChecking=accept-new, ConnectTimeout
- nur EIN Migration-Lauf gleichzeitig (Lock)
- Ziel: automatisches Safety-Backup der kritischen Configs VOR Überschreiben
- keine Secrets ins Log

## Akzeptanzkriterien
- [ ] Von der Migration-Seite am Quellserver lässt sich mit Ziel-Adresse + SSH-Key
      ein Voll-Klon anstoßen
- [ ] rsync überträgt inkrementell; zweiter Lauf nur Delta
- [ ] `vms/` (root-owned) + 894-GB-Archive landen vollständig auf dem Ziel
- [ ] Ownership/Permissions auf Ziel korrekt (hydrahive:hydrahive, /etc 640)
- [ ] DB konsistent (Snapshot, nicht offenes WAL)
- [ ] Live-Log sichtbar; Abbruch/Fehler klar gemeldet; resumierbar
- [ ] Ziel-HydraHive startet nach Migration mit identischem Zustand
- [ ] Excludes greifen (kein node_modules/venv-Ballast)
- [ ] Tests: Router-Validierung, Trigger-Datei-Format, Exclude-Logik, Preflight

## Auth: Passwort (Till-Entscheidung)

SSH-Passwort-Authentifizierung via `sshpass` (auf Quellserver verifiziert
vorhanden). Ablauf:
- Migrations-Dialog: Ziel-Host, SSH-Port, SSH-User (default `root`), **Passwort**.
- Passwort wird NICHT in der `.migration_request`-Trigger-Datei im Klartext auf
  Platte gelegt. Stattdessen: Core schreibt das Passwort in eine separate Datei
  mit `chmod 600` (root:hydrahive) ODER übergibt es via named pipe / Env an den
  oneshot-Service. Bevorzugt: eigene Datei `.migration_secret` (0600), die
  migrate.sh nach Einlesen sofort löscht. Niemals ins Log.
- `sshpass -f <secretfile> ssh/rsync ...` — Passwort nie in der Prozessliste
  (kein `-p` mit Argument, sondern `-f` File oder `-e` Env).
- `StrictHostKeyChecking=accept-new` (erster Kontakt), Host-Key wird gemerkt.

## Offene Punkte
- Bandbreiten-Limit (`--bwlimit`) als Option, damit Prod nicht erstickt? →
  als optionales Feld im Dialog, default aus.
- Separater Bug (eigener Task): normales tar.gz-System-Backup übergeht
  workspaces/ + modules/ — für kleine Backups trotzdem fixen.
