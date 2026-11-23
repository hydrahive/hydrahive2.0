# Update mit Sicherung und Rückweg

**Stand:** 23.11.2026 · **Status:** Entwurf, wartet auf Freigabe durch Till · **Task:** 5b8ad460
**Zieldokument:** `hydrahive2-modules/ziele/bewertung-auth-update.md` §2 (freigegeben 23.11.2026)
**Verwandt:** `update-git-sicher.md`, `system-updates.md`, `mac-update.md`, `modul-update-alle.md`,
`server-migration-rsync.md`, Task cd72a1ad (Server klonen)

Nur Spec. Gebaut wird erst nach Tills Freigabe, in den Etappen aus §7.

## 1. Ziel

Heute legt weder `installer/update.sh` (919 Zeilen) noch `installer/update-mac.sh` (279 Zeilen) eine Sicherung an,
und es gibt keinen Rückweg. Scheitert der Frontend-Bau, eine Migration oder der Start, bleibt der Server auf einem
halben Stand stehen. Beleg aus dem Update-Log auf .4: Ein Lauf endete mit
`HH-UPDATE-ENDE: fehler Abbruch (Code 2)` nach `error TS2307` im `tsc -b`. Da war der Code schon gezogen,
`node_modules` neu installiert und `dist/` halb gebaut.

Ziel ist:

1. **Vor jeder Änderung** den alten Commit merken und den Kern-Datenbestand sowie die Konfiguration konsistent
   sichern. Reicht der Platz nicht, bricht das Update **vor jeder Änderung** mit einer klaren Meldung ab.
2. **Nach dem Update** gilt es erst als erfolgreich, wenn alle drei Bedingungen erfüllt sind: der Dienst ist aktiv,
   `/api/health` antwortet mit `status: ok` **und dem neuen Commit**, und die Migrationen sind durchgelaufen.
3. **Bei Fehlschlag** geht es automatisch zurück auf den alten Commit, den alten Build und venv und die alte DB.
   Danach wird der Dienst gestartet. Das Update-Fenster zeigt
   `HH-UPDATE-ENDE: fehler <Grund> – auf <alter Commit> zurückgesetzt`.
4. **Der Rückweg verliert nie Daten.** Bevor eine Sicherung eingespielt wird, kommt der kaputte Stand zur Seite.
   Er wird nicht gelöscht.
5. **Modul-Updates:** Die alte Modulversion bleibt erhalten, bis die neue läuft.

Nicht-Ziele (laut Zieldokument): keine Prozess-Isolation von Modulen (`dea1413d`), kein Commit-Pinning und keine
Signatur (`2c73f4b5`). Ebenfalls nicht Ziel: apt-Pakete, Container und Fremd-Repos (AgentLink) zurückzudrehen,
siehe §2.3.

## 2. Bestandsbild

Stand: Kern `6e556249` (main, 23.11.2026). Zeilenangaben beziehen sich auf `installer/update.sh`. Gemessen auf dem
Server .4 (HydrahiveHome), nur lesend, die Sicherungen wurden nach /tmp geschrieben und danach gelöscht.

### 2.1 Was update.sh ändert und ob es umkehrbar ist

Spalte „Umkehrbar“: **ja** = mit einer Sicherung vor dem Update exakt zurückzuholen;
**idempotent** = der Schritt repariert nur einen Soll-Zustand, und der alte Code verträgt den neuen Zustand
(Zurückdrehen ist unnötig); **nein** = nicht sinnvoll zurückzuholen.

| # | Zeilen | Schritt | Ändert | Umkehrbar | Bei Fehler heute |
|---|---|---|---|---|---|
| 1 | 52–68 | SSH-Verzeichnis, `known_hosts`, ssh-Include | `/home/hydrahive/.ssh`, `chown -R` auf das Home | idempotent | `set -e` → Abbruch |
| 2 | 70–101 | `hh_git_update` (lib/git-update.sh): `fetch` + `merge --ff-only`; bei History-Rewrite Tag `hh-update-vorher-*` + `reset --hard`; danach Re-exec, falls sich update.sh geändert hat | Arbeitsbaum `/opt/hydrahive2` | **ja**, alter Commit per `git reset --hard <alt>` (der Arbeitsbaum ist vorher sauber, Z. 34–37 der lib) | `err` → Abbruch **vor** jeder weiteren Änderung |
| 3 | 109–113 | `repair_llm_config_permissions` | Rechte von `llm.json` | idempotent | — |
| 4 | 115–126 | Host-Selbstheilung (tmpfs, resolved-Stub, incus-DNS, Pi-hole) | `/etc/fstab`, systemd-resolved, incus-Netz | idempotent, nicht zurückdrehen | teils Abbruch |
| 5 | 128–134 | `hh_system_upgrade`: **apt-Vollupgrade des ganzen Systems** (system-updates.md) | Systempakete | **nein** (kein apt-Rollback) | nie fatal |
| 6 | 136–142 | Dokument-Werkzeuge, sudoers-Heilung | apt, `/etc/sudoers.d/` | idempotent | — |
| 7 | 144–161 | `hh_ensure_python_venv`: bei neuem System-Python `venv --clear` und Neubau; Voice-Bridge wird vorher angehalten | `/opt/hydrahive2/.venv` (669 MB) | **ja**, wenn das venv vorher gesichert wurde (Kopie gemessen: 13,9 s) | Abbruch |
| 8 | 163–197 | Node.js 20 (NodeSource) und npm-Reparatur (corepack, `/usr/local/bin/npm`) | apt, `/usr/local/bin/npm` | nein, idempotent | Abbruch |
| 9 | 199–201 | `pip install -e core` | `.venv` | **ja**, über die venv-Sicherung | Abbruch |
| 10 | 203–256 | graphify, llmfit, Local Media (`72-local-media.sh`), Playwright-Chromium, dev-browser, mmx-cli | `~/.cache`, `/usr/local/bin`, Container `hydra-comfyui` | nein, versions-idempotent | meist `|| log … weiter` |
| 11 | 258–266 | `chown -R` auf das Repo, `npm ci`, **`npm run build`** (`tsc -b && vite build`) | `frontend/node_modules` (554 MB), `frontend/dist` (101 MB), dazu generierte Dateien im Arbeitsbaum | **ja**, über die `dist`-Sicherung (Kopie gemessen: 1,2 s); `node_modules` baut `npm ci` aus dem alten Lock neu | **Abbruch mit halbem `dist`** und neuem Code, Dienst läuft noch mit altem Code im Speicher |
| 12 | 268–275 | WhatsApp-Bridge `npm ci` | `node_modules` der Bridge | idempotent | Abbruch |
| 13 | 277–585 | systemd-Units der Trigger anlegen (update, restart, samba, migration, bridge, voice, local-media, addon), nur wenn sie fehlen | `/etc/systemd/system/hydrahive2-*.{service,timer}` | idempotent (nur Neuanlage) | — |
| 14 | 430–436 | smb.conf-Heilung, ggf. `47-samba.sh` | `/etc/samba` | idempotent | `|| log weiter` |
| 15 | 587–650 | sshpass, gh, VM-Manager (`65-vms.sh`), qemu-bridge-helper, incus (`70-containers.sh`), NAT, hh-portforward | apt, `/etc/qemu`, incus | **nein** (Pakete, Container-Runtime) | `|| log weiter` |
| 16 | 652–732 | Voice-Container (autostart/start), `55-voice.sh`, Bestandsmigrationen `voice-stt-perf`, `pin-venv-python`, SearXNG-venv, `searxng-engines` | incus-Container, `/opt/searxng` | **nein** im Sinne dieser Spec (Container); `searxng-engines.sh` sichert selbst | `|| log … weiter` |
| 17 | 746–804 | Unit `hydrahive2.service` per `50-systemd.sh` neu schreiben, sudoers ergänzen | `/etc/systemd/system/hydrahive2.service`, `/etc/sudoers.d/hydrahive2-extensions` | **ja**, wenn die Unit-Datei vorher gesichert wurde | `|| log "systemd-rewrite failed — weiter"` |
| 18 | 806–842 | nginx-Config per `60-nginx.sh` neu schreiben | `/etc/nginx/sites-available/hydrahive2` | **ja**, mit Sicherung der Datei | `|| log … weiter` |
| 19 | 844–859 | AgentLink: `git pull --ff-only` in `/opt/hydralink` (1,8 GB) + eigener Installer | Fremd-Repo, eigene DB, eigene Dienste | **nein** in dieser Spec (eigenes Repo, eigener Rückweg; Fehlschlag beendet das Update nicht) | laute Meldung, weiter |
| 20 | 861–884 | Go-cgo, Tailscale (`80-tailscale.sh`), PostgreSQL-Mirror (`48-postgres.sh`) nur wenn er fehlt | apt, PostgreSQL-Cluster | nein, idempotent | `|| log weiter` |
| 21 | 886–897 | Credential-Verzeichnis, `write_service_secrets` | `/etc/hydrahive2/extensions`, `/etc/hydrahive2/service-secrets.env` | **ja** über die Sicherung von `/etc/hydrahive2` | Warnung, alte Datei bleibt |
| 22 | 899–900 | **`systemctl restart hydrahive2.service`** → beim Start laufen die DB-Migrationen (§2.2) | **`sessions.db`** | **ja, nur mit DB-Sicherung**; es gibt keine Down-Migrationen | — |
| 23 | 902–919 | Voice-Bridge (try-)restart, danach **nur `is-active`**, kein `/api/health` | — | — | `exit 1` mit „Service-Neustart fehlgeschlagen“; `Restart=on-failure` (5 s) startet in Schleife |

Nebenbefund (eigener Bug, nicht Teil dieser Spec): `installer/modules/47-samba.sh:89` setzt bei jedem Lauf
`chown -R` sowie `chmod` auf alle Dateien unter `workspaces`. Das kostet Zeit, verändert Rechte in den Workspaces
und lässt sich nicht zurückdrehen (siehe Task cd72a1ad).

### 2.2 Migrationen beim Start

- **Kern:** `api/lifespan.py` → `init_db()` (`db/connection.py:14`) → `apply_migrations()` (`db/migrations.py`).
  Die Dateien `db/migrations/NNN_*.sql` (aktuell 066) laufen per `executescript`, die Versionen stehen in
  `schema_version`. Es gibt **keine Down-Migrationen**. Fehler mit „duplicate column name“ oder „already exists“
  werden als „partiell angewendet“ übersprungen, alle anderen werfen eine Exception und **der Start scheitert**.
  2 der 66 Dateien enthalten `DROP`/`RENAME`, Daten können also auch verloren gehen.
- **Module:** `modules/loader.py:108` → `apply_module_migrations()`. Sie laufen in **derselben `sessions.db`**
  (Tabelle `module_schema_version`, 87 Einträge in 29 Modulen). Scheitert eine, gilt nur **dieses Modul** als
  „nicht geladen“ (`LoadedModule.error`), der Dienst startet trotzdem und `/api/health` meldet `ok`.
- **Weitere Schreibvorgänge beim Start:** `install_system_defaults()` (System-Skills), `ensure_admin`,
  `agent_bootstrap.migrate_tools()` (Agenten-Configs unter `agents/*/config.json`),
  `ensure_required_bundled_modules()` (kopiert fehlende Pflichtmodule) und `pg_mirror.init()` mit DDL im Mirror
  (`ALTER TABLE … DROP/ADD COLUMN IF NOT EXISTS embedding`).
- **Folge:** Nach dem Neustart passt der alte Code womöglich nicht mehr zur DB. Wer zurückwill, braucht **den alten
  Commit und die DB-Sicherung gemeinsam**.

### 2.3 Modul-Update-Wege (eigener Ablauf, nicht in update.sh)

| Weg | Code | Ändert | Alte Version bleibt? |
|---|---|---|---|
| Install | `copy_module_in` (`modules/installer.py:106`) | `rmtree` + `copytree` nach `/var/lib/hydrahive2/modules/<id>` und `frontend/src/modules/<id>` | entfällt (neu) |
| Update (einzeln, „alle“) | `replace_module_in` (`:171`), `update_all.py` | Neuer Stand wird in einem Temp-Ordner vorbereitet, dann `rename`; der alte Stand liegt nur **bis zum Ende des `TemporaryDirectory`** als `previous` vor und wird danach **gelöscht**. Das Frontend wird per `_replace_frontend` direkt ersetzt (`rmtree`). | **nein**: Der alte Code ist weg, bevor gebaut und neu gestartet wurde |
| danach | `_frontend_build()` (`npm run build` ohne `npm ci`), `_request_restart()` | `frontend/dist`, Neustart, Modul-Migrationen | Bau-Fehler → `dist` halb neu, kein Rückweg |

Module liegen in `/var/lib/hydrahive2/modules` (29 Module, 33 MB) und `frontend/src/modules` (7 MB).

### 2.4 Datenbanken und Daten

| Bestand | Ort | Größe (.4) | Gesichert? |
|---|---|---|---|
| **`sessions.db`** (Kern **und** alle Module, WAL-Modus) | `/var/lib/hydrahive2/sessions.db` | **9,09 GB**, davon **rund 80 % freie Seiten** (1,78 von 2,22 Mio. Seiten à 4 KiB) | nein |
| `hydrahive.db`, `datamining.db` | `/var/lib/hydrahive2/` | 0 Byte (Altlasten) | entfällt |
| PostgreSQL-Mirror `hydrahive_mirror` (Datamining, pgvector) | PG 18, `/var/lib/postgresql/18/main` | nicht messbar (keine Rechte) | nein. Er wird aus `sessions.db` nachgezogen (`_mirror_catchup`, `ON CONFLICT DO NOTHING`), braucht also keine Sicherung für den Rückweg |
| AgentLink-DB | eigener Dienst, `/opt/hydralink` | — | außerhalb dieser Spec |
| Konfiguration `/etc/hydrahive2` (`install.conf`, `secret_key`, `service-secrets.env`, `llm.json`, `pg_mirror.dsn`, `extensions/`) | `/etc/hydrahive2` | für Agenten gesperrt, nicht gemessen; klein (Text-Dateien) | nein. **Das Update läuft als root und kann es sichern.** |
| JSON-Daten (Agenten-Configs, Users, Credentials, Projekte, Skills) | `/var/lib/hydrahive2/{agents,users,credentials,projects,skills,plugins,peering}` | `agents/` 309 MB (fast nur Sitzungs-Dateien; die Configs selbst: 69 JSON-Dateien, ca. 2 MB), Rest < 1 MB | nein |
| Kleine Modul-/Erweiterungs-DBs | `extensions/paperless-ngx/…/db.sqlite3` (1,3 MB), `aig-runtime/db/tasks.db`, `mailbox/archiv/index.sqlite` | < 2 MB | nicht Teil des Kern-Rückwegs |
| Workspaces | `/var/lib/hydrahive2/workspaces` (HDD `sda2`) | groß | **nein, bewusst nicht** (Nutzdaten, ändert ein Update nicht) |

Platz: `/var/lib/hydrahive2` liegt auf der SSD `md127` (469 GB, **412 GB frei**). Die Workspaces liegen auf der
HDD `sda2` (15 TB frei).

### 2.5 Messung: Zeit und Platz einer Sicherung (.4, laufender Dienst, `ionice -c3 nice 19`)

| Verfahren | Zeit | Ergebnis |
|---|---|---|
| `sqlite3`-CLI `.backup` | **bricht nie ab**: Nach über 2 min und 44 GB Lesen stand die Datei immer noch bei 5,05 GB. Jede Schreibung des Dienstes startet die schrittweise Kopie neu. | **ungeeignet** |
| Python `sqlite3.backup(dst, pages=-1)` (ein Schritt, kurze Lese-Sperre) | **62,8 s** | 9,09 GB (mit den freien Seiten) |
| **`VACUUM INTO '<ziel>'`** (konsistenter Lese-Snapshot) | **21,6 s** (HDD-Ziel 26,8 s) | **1,78 GB** |
| `PRAGMA quick_check` der Sicherung | 0,8 s | `ok` (`integrity_check`: 2,0 s, `ok`) |
| zstd `-3 -T0` | 2,3 s | **452 MB** |
| zstd entpacken | 1,6 s | — |
| Rückkopie 9,09 GB per `cp` (Ziel /tmp, HDD) | 152 s | — |
| Rückkopie 1,78 GB per `cp` (HDD) | 9,5 s | — |
| kaputten Stand zur Seite legen (`mv`, gleiches Dateisystem) | 0,03 s | — |
| venv kopieren (669 MB) / `dist` kopieren (101 MB) | 13,9 s / 1,2 s | — |

**Folgerung:** `VACUUM INTO` ist hier das Mittel der Wahl. Es ist dreimal schneller als `backup()`, belegt nur
ein Fünftel des Platzes und liefert gleich eine kompakte, geprüfte Datei. Eine vollständige Kern-Sicherung
(DB + venv + dist + `/etc/hydrahive2` + Unit/nginx) kostet auf .4 **rund 40 s und rund 2,6 GB** unkomprimiert,
mit zstd für die DB rund 1,2 GB. Der Rückweg braucht rund 10–15 s für die DB plus den Neustart.

Hinweis: Die Messung lief auf .4. Größe und Laufzeit hängen von der DB ab. Auf dem Mac und auf kleinen Installationen
ist beides deutlich kleiner.

## 3. Ablauf

_(folgt)_

## 4. Fehlerfälle

_(folgt)_

## 5. Mac-Unterschiede

_(folgt)_

## 6. Aufbewahrung

_(folgt)_

## 7. Etappen

_(folgt)_

## 8. Offene Fragen an Till

_(folgt)_
