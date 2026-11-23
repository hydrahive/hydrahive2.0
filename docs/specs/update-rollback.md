# Update mit Sicherung und Rückweg

**Stand:** 23.11.2026 · **Status:** FREIGEGEBEN (Till, 23.11.2026: „alle Vorschläge ok“) · **Task:** 5b8ad460
**Zieldokument:** `hydrahive2-modules/ziele/bewertung-auth-update.md` §2 (freigegeben 23.11.2026)
**Verwandt:** `update-git-sicher.md`, `system-updates.md`, `mac-update.md`, `modul-update-alle.md`,
`server-migration-rsync.md`, Task cd72a1ad (Server klonen)

Gebaut wird in den Etappen aus §7. Die Fragen aus §8 sind entschieden: Es gelten jeweils die Vorschläge.

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

Neue Bibliothek `installer/lib/update-safety.sh`, die `update.sh` sourct. Python-Hilfen liegen als kleines Skript
`installer/lib/db_snapshot.py`, das mit dem System-`python3` läuft und nicht mit dem venv, denn das venv ist ja
Gegenstand des Rückwegs. Jeder Lauf bekommt einen Sicherungsordner:

```
/var/lib/hydrahive2/backups/update/<UTC-Zeit>_<alter-commit-kurz>/
  meta.env            # OLD_COMMIT, OLD_BRANCH, NEW_COMMIT (nach dem pull), Start, Status
  sessions.db.zst     # VACUUM INTO + quick_check + zstd
  etc-hydrahive2.tar  # /etc/hydrahive2, root:root 0600
  units/              # hydrahive2.service (+ .d/), nginx sites-available/hydrahive2, sudoers.d/hydrahive2-extensions
  venv.tar.zst        # nur wenn Python oder Abhängigkeiten sich ändern (siehe 3.1, Schritt 5)
  dist/               # frontend/dist (Hardlink-Kopie bzw. cp)
  modules-frontend/   # frontend/src/modules (generiert, gitignored)
```

Der Ordner gehört `root:root` und hat die Rechte `0700`, denn er enthält Geheimnisse aus `/etc/hydrahive2`.

### 3.1 Phase A – Vorbereitung (vor jeder Änderung)

1. **Sperre:** `flock` auf `/run/hydrahive2-update.lock`. Läuft schon ein Update, endet der zweite Lauf mit
   `fehler Update läuft bereits`.
2. **Alten Stand merken:** `OLD_COMMIT=$(git rev-parse HEAD)` und den Branch. Diese Werte stehen in `meta.env`,
   **bevor** `hh_git_update` läuft. Der Re-exec (Z. 99) übernimmt `HH_BACKUP_DIR` per Umgebung, damit nach dem Re-exec
   keine zweite Sicherung entsteht.
3. **Platzprüfung:** Bedarf schätzen = `page_count − freelist_count` × `page_size` (Nutzdaten der DB) × 1,2
   + Größe von `dist` + (venv, falls es gesichert wird) + 1 GB Puffer.
   Ist auf dem Dateisystem des Sicherungsordners **und** auf dem von `sessions.db` (wegen der WAL) zu wenig frei,
   endet der Lauf mit `err "Zu wenig Platz für die Sicherung: frei X GB, nötig Y GB – nichts verändert"`.
   Auf .4: nötig rund 3 GB, frei 412 GB.
4. **DB sichern:** `VACUUM INTO` in eine Temp-Datei im Sicherungsordner, dann `PRAGMA quick_check` = `ok`, dann
   `zstd`, dann `fsync` und `rename`. Scheitert das, endet der Lauf mit `err`, es ist noch nichts verändert.
5. **Rest sichern:** `/etc/hydrahive2` (tar), Unit-, nginx- und sudoers-Dateien, `frontend/dist`,
   `frontend/src/modules`. Das venv wird gesichert, wenn `hh_venv_needs_rebuild` zutrifft oder wenn sich
   `core/pyproject.toml` zwischen `OLD_COMMIT` und `origin/<branch>` ändert. Das lässt sich nach dem `fetch` prüfen.
   Sonst genügt `pip install -e` mit dem alten Commit. Siehe offene Frage F3.
6. `meta.env`: `STATUS=gesichert`.

Zeit auf .4: rund 25 s (DB) + 2 s (Rest), mit venv rund 40 s.

### 3.2 Phase B – Update

Unverändert wie heute (Z. 70–897), mit drei Änderungen:

- `NEW_COMMIT` nach `hh_git_update` in `meta.env` schreiben.
- Ab hier ist **jeder** Fehler ein Rückweg-Fall: Der `trap` ruft vor der Schlusszeile `hh_rollback`, wenn
  `STATUS` mindestens `gesichert` ist und der Commit sich geändert hat. Fehler **vor** der Sicherung, etwa
  „Lokale Änderungen …“ oder fehlendes Netz, brauchen keinen Rückweg und enden wie heute mit „nichts verändert“.
- **Frontend-Bau getrennt:** `vite build --outDir dist.neu` und erst bei Erfolg `dist` gegen `dist.neu` tauschen.
  Dann bleibt ein Bau-Fehler ohne Wirkung auf das laufende Frontend. Das ist schon für sich ein Gewinn (Etappe U2).

### 3.3 Phase C – Prüfung nach dem Neustart

Nach `systemctl restart hydrahive2.service` (Z. 900) wird bis zu **120 s** (einstellbar `HH_UPDATE_HEALTH_TIMEOUT`)
alle 2 s geprüft:

1. `systemctl is-active hydrahive2.service`, dazu `NRestarts` unverändert (so fällt eine Neustart-Schleife durch
   `Restart=on-failure` auf).
2. `curl -fsS http://$HH_HOST:$HH_PORT/api/health` liefert `status == "ok"` **und** `commit == NEW_COMMIT`
   (kurz). Der Endpunkt gibt den Commit heute schon aus (`api/main.py:285`).
3. **Migrationen durchgelaufen:** `MAX(version)` in `schema_version` ist mindestens die höchste Nummer unter
   `core/src/hydrahive/db/migrations/` des neuen Commits. Das ist ein read-only-Zugriff mit `python3`.
   Kern-Migrationen, die scheitern, verhindern den Start ohnehin. Gescheiterte **Modul**-Migrationen siehe F4.

Erst wenn alle drei Prüfungen bestehen, steht `STATUS=ok`, dann folgt `HH-UPDATE-ENDE: ok` und die Aufräumregel aus §6.

### 3.4 Phase D – Rückweg (`hh_rollback`)

Jeder Schritt wird protokolliert. Ein Fehler in einem Rückweg-Schritt bricht den Rückweg **nicht** ab, er wird
gesammelt und in der Schlusszeile gemeldet.

1. `systemctl stop hydrahive2.service` (dazu die Voice-Bridge, die dasselbe venv nutzt).
2. **Kaputten Stand zur Seite legen, nicht löschen:** `sessions.db`, `-wal` und `-shm` per `mv` (gleiches
   Dateisystem, 0,03 s) nach `<sicherungsordner>/kaputt/`. Die geänderten Dateien aus `/etc/hydrahive2` werden
   ebenfalls dorthin kopiert, dazu `git diff OLD_COMMIT..NEW_COMMIT --stat`. Erst danach wird irgendetwas
   eingespielt.
3. **Code:** `git reset --hard OLD_COMMIT` als Dienstnutzer. Der Arbeitsbaum war vor dem Update sauber
   (lib/git-update.sh lehnt sonst ab), und eine umgeschriebene `package-lock.json` gehört zu den erlaubten Dateien.
   Der Branch bleibt, nur die Spitze wird zurückgesetzt.
4. **Build:** `frontend/dist` und `frontend/src/modules` aus der Sicherung zurückholen, kein Neubau. Danach
   `npm ci` im Hintergrund oder beim nächsten Update, denn `node_modules` braucht der laufende Dienst nicht.
5. **venv:** Gab es eine Sicherung, wird sie zurückgeholt, sonst läuft `pip install -e core` mit dem alten Stand.
   Scheitert das, wird es gemeldet, aber die Schritte 6–8 laufen trotzdem.
6. **DB:** `sessions.db.zst` entpacken (1,6 s) nach `sessions.db.neu`, `quick_check`, Besitzer `hydrahive`,
   dann `rename` auf `sessions.db`.
7. **Konfiguration:** Unit-, nginx- und sudoers-Dateien sowie `/etc/hydrahive2` zurückspielen,
   `systemctl daemon-reload`, `nginx -t && systemctl reload nginx`.
8. `systemctl start hydrahive2.service`, dann dieselbe Prüfung wie in 3.3, diesmal mit `commit == OLD_COMMIT`.
9. Schlusszeile:
   - gelungen: `HH-UPDATE-ENDE: fehler <Grund> – auf <OLD_COMMIT kurz> zurückgesetzt`
   - Rückweg selbst gescheitert: `HH-UPDATE-ENDE: fehler <Grund> – Rückweg unvollständig (<Schritt>), Sicherung in <Pfad>`

   Das Update-Fenster (`frontend/src/shared/_updateLogStatus.ts`, Muster `^HH-UPDATE-ENDE: (ok|fehler)(?: (.*))?$`)
   zeigt den Zusatz ohne Änderung an, denn er gehört zum Grund.
10. `meta.env`: `STATUS=zurueckgesetzt` bzw. `STATUS=rueckweg_unvollstaendig`. Solche Ordner räumt §6 **nie** auf.

**Was der Rückweg bewusst nicht anfasst:** apt-Pakete (Schritt 5 und 8 der Tabelle), Container und incus,
AgentLink, den PostgreSQL-Mirror (er holt sich fehlende Events selbst aus `sessions.db`, Zeilen aus der Zeit
zwischen Sicherung und Rückweg bleiben dort liegen und sind harmlos) sowie die Workspaces.

**Daten zwischen Sicherung und Rückweg:** Was Nutzer in der Zeit zwischen Phase A und dem Stopp geschrieben haben
(Chat-Nachrichten im laufenden alten Dienst, typisch 1–5 min), steckt nur in der zur Seite gelegten
`kaputt/sessions.db`. Es geht nicht verloren, kommt aber nicht automatisch zurück. Siehe F2.

### 3.5 Modul-Updates (`modules/installer.py`)

- `replace_module_in` behält `previous` **nicht** im Temp-Ordner, sondern verschiebt den alten Stand nach
  `/var/lib/hydrahive2/modules/.previous/<id>/` (Backend) und `…/.previous/<id>/frontend/` (Frontend-Quelle).
  Vorher: `frontend/dist` sichern.
- Danach `_frontend_build()` in `dist.neu`. Bei einem Fehler: Modul aus `.previous` zurück, das alte `dist` bleibt
  bestehen, und es gibt **keinen** Neustart. Meldung: `[modules] <id>: Bau fehlgeschlagen – alte Version bleibt`.
- Nach dem Neustart prüft der Lader beim Start, ob das Modul `loaded` ist. Wenn nicht, wird es als „fehlerhaft nach
  Update“ gekennzeichnet, und das Cockpit bietet „alte Version zurückholen“ an (Modul aus `.previous` zurück, Bau,
  Neustart). Automatisch zurück geht es nur beim Bau-Fehler. Ein automatischer Rückweg nach dem Neustart würde eine
  zweite Neustart-Runde brauchen, siehe F5.
- Modul-Migrationen laufen in `sessions.db`. Vor einem Modul-Update wird daher dieselbe DB-Sicherung angelegt
  (`VACUUM INTO`, rund 25 s auf .4). `.previous/<id>` wird beim nächsten erfolgreichen Update desselben Moduls
  ersetzt.

## 4. Fehlerfälle

| # | Fehler | Wann | Verhalten neu | Schlusszeile |
|---|---|---|---|---|
| E1 | Zu wenig Platz | Phase A | Abbruch vor jeder Änderung | `fehler Zu wenig Platz für die Sicherung: frei X GB, nötig Y GB – nichts verändert` |
| E2 | `VACUUM INTO` oder `quick_check` scheitert (DB gesperrt, defekt) | Phase A | Abbruch vor jeder Änderung; Temp-Datei weg | `fehler DB-Sicherung fehlgeschlagen (<Grund>) – nichts verändert` |
| E3 | Lokale Änderungen, abweichende Commits, fetch scheitert | Git-Schritt | wie heute, kein Rückweg nötig | wie heute (`… nichts verworfen`) |
| E4 | apt, Node oder npm-Reparatur scheitert (`set -e`) | Phase B | Rückweg (der Code ist schon neu) | `fehler <Grund> – auf <alt> zurückgesetzt` |
| E5 | `pip install -e core` scheitert | Phase B | Rückweg inklusive venv | dito |
| E6 | `npm ci` oder `npm run build` scheitert (Beleg TS2307) | Phase B | `dist` unberührt (Bau in `dist.neu`), Rückweg für Code und venv, **kein** DB-Rückweg nötig, weil kein Neustart war → DB-Schritt wird übersprungen | dito |
| E7 | Kern-Migration wirft → Dienst startet nicht oder hängt in der Neustart-Schleife | Phase C | Rückweg inklusive DB | dito |
| E8 | Dienst aktiv, aber `/api/health` antwortet nicht oder meldet den falschen Commit (Import-Fehler im Lifespan, Port belegt) | Phase C | nach Ablauf der Wartezeit Rückweg inklusive DB | `fehler Health-Prüfung nach 120 s nicht ok – auf <alt> zurückgesetzt` |
| E9 | Modul-Migration scheitert (Modul nicht geladen, Dienst ok) | Phase C | **kein** Rückweg des Kerns, Warnung im Log und im Cockpit (F4) | `ok` + Warnzeile |
| E10 | `|| log … weiter`-Schritte (Samba, VMs, Voice, nginx-Rewrite, Postgres, Tailscale) scheitern | Phase B | wie heute: kein Rückweg, aber Warnungen gesammelt und zum Schluss als `HH-UPDATE-WARNUNG: …` ausgegeben | `ok` |
| E11 | AgentLink-Update scheitert | Phase B | wie heute: laut, kein Rückweg des Kerns | `ok` + Warnung |
| E12 | Rückweg selbst scheitert (z. B. `git reset`, Platz) | Phase D | weiter mit den nächsten Schritten; der Dienst wird in jedem Fall gestartet; `kaputt/` und die Sicherung bleiben erhalten | `fehler <Grund> – Rückweg unvollständig (<Schritt>), Sicherung in <Pfad>` |
| E13 | Update-Prozess wird hart beendet (Stromausfall, `kill -9`, Reboot durch apt) | jederzeit | Beim nächsten Start von `update.sh` (und per `ExecStartPre` des Dienstes, F6) gilt: Steht in einem Sicherungsordner `STATUS=gesichert` ohne Abschluss, wird das gemeldet und der Rückweg angeboten bzw. durchgeführt | `fehler Vorheriges Update unterbrochen – …` |
| E14 | Re-exec nach Änderung von update.sh | Git-Schritt | `HH_BACKUP_DIR` und `OLD_COMMIT` werden über die Umgebung weitergereicht, keine zweite Sicherung | — |
| E15 | Ein Commit enthält eine Migration, die der alte Code nicht verträgt, und die DB-Sicherung fehlt (z. B. manuell gelöscht) | Phase D | **kein** Code-Rückweg ohne DB: Der Dienst bleibt auf dem neuen Code und es gibt eine klare Meldung. Lieber ein halber Dienst als ein alter Code auf einer neuen DB. | `fehler … – Rückweg nicht möglich: DB-Sicherung fehlt` |

**Grundsatz:** Rückweg-Code und Sicherungs-Code stammen aus dem Stand **vor** dem `git pull`. Die Bibliothek wird
**vor** dem `git pull` nach `<sicherungsordner>/update-safety.sh` kopiert und von dort gesourct. So kann ein kaputter
neuer Stand seinen eigenen Rückweg nicht beschädigen. Auch nach einem Re-exec sourct die neue update.sh den Rückweg
aus dieser Kopie (Pfad per `HH_BACKUP_DIR`). Nur Sicherung und Prüfung, die vor dem Neustart liegen, dürfen aus dem
neuen Stand kommen.

## 5. Mac-Unterschiede

| Punkt | Linux (`update.sh`) | macOS (`update-mac.sh`) | Folge für diese Spec |
|---|---|---|---|
| Pfade | Daten `/var/lib/hydrahive2`, Config `/etc/hydrahive2` | Daten `/usr/local/var/hydrahive2`, Config `/usr/local/etc/hydrahive2` (Z. 8–11) | Pfade aus denselben Variablen (`HH_DATA_DIR`, `HH_CONFIG_DIR`), Sicherung unter `$HH_DATA_DIR/backups/update/` |
| Git | `hh_git_update` (lib/git-update.sh, verwirft nichts) | **`git pull --ff-only`** direkt (Z. 67), ohne Prüfung auf lokale Änderungen | Zuerst auf `hh_git_update` umstellen (Etappe U5), sonst ist `OLD_COMMIT` + `reset --hard` riskant |
| Dienst | systemd, `systemctl restart` (Z. 900), `Restart=on-failure` | launchd: `launchctl unload` + `load` der Backend-plist (Z. 274–277); bei plist-Umbau `exit 0` **ohne eigenen Neustart-Check** (Z. 270–271) | Prüfung (3.3) gilt auch für den plist-Umbau-Pfad; „aktiv“ = `launchctl print system/io.hydrahive.backend` mit `state = running` |
| Frontend | baut immer | baut nur, wenn `dist/.hh-frontend-rev` ≠ letzter Commit unter `frontend/` (Z. 105–127) | Bau in `dist.neu` + Tausch; der Merker wird erst nach dem Tausch geschrieben |
| Python | `hh_ensure_python_venv` (Neubau bei neuem Interpreter) | `pip install -e` + `hh_mac_heal_python` (Z. 93–103) | venv-Sicherung nach derselben Regel (3.1, Schritt 5) |
| Sicherungswerkzeuge | `python3`, `zstd` vorhanden | System-`python3` (`/usr/bin/python3`, CLT) hat `sqlite3` mit `VACUUM INTO`; **`zstd` ist nicht garantiert** | Mac: `gzip` statt `zstd`, oder unkomprimiert (die Mac-DBs sind klein) |
| Root/Homebrew | Update läuft als root | root darf nichts aus dem Homebrew-Prefix ausführen (Z. 49–62) | Sicherungs-Skript nur mit `/usr/bin/python3`, `/usr/bin/tar`, `/usr/bin/gzip` |
| Fehler heute | `set -e` + `err` | jeder Schritt mit `|| fail` oder `|| log` | gleiche Rückweg-Regeln (Fehler ab Phase B → Rückweg) |
| Vorbild | — | `lib/mac-migrate-rollback.sh`: Rückweg beim Umzug auf das Dienst-Konto (Dienste stoppen, Dateien aus der Sicherung, Dienste starten, DB zuerst) | Muster für `hh_rollback` auf dem Mac; der Dienst-Konto-Umzug selbst bleibt mit seinem eigenen Rückweg (er endet mit `exit 0`, Z. 148–149) |
| Weitere Dienste | Voice-Bridge teilt das venv | PostgreSQL, Colima, AgentLink und Voice als eigene LaunchDaemons | nur das Backend wird zurückgedreht; die anderen wie Linux E10/E11 |

Der Mac kommt als **eigene Etappe** nach Linux (U5). Getestet wird auf dem Test-Mac .186, und nur mit Rücksprache.

## 6. Aufbewahrung

- Vorschlag: **die letzten 2 erfolgreichen Sicherungen** (`STATUS=ok`) bleiben, ältere löscht ein erfolgreiches
  Update am Ende. Auf .4 sind das rund 2 × 1,2 GB (DB komprimiert + dist + Config; das venv nur, wenn gesichert).
- **Nie automatisch gelöscht** werden Ordner mit `STATUS=zurueckgesetzt`, `rueckweg_unvollstaendig` oder
  `gesichert` (unterbrochen), ebenso jeder `kaputt/`-Ordner. Sie werden im System-Fenster angezeigt
  („Sicherung von <Datum>, <Grund>“) und nur von Hand gelöscht, mit Bestätigung.
- Obergrenze: Belegen die Sicherungen mehr als 10 % des freien Platzes, gibt es eine Warnung im Dashboard, aber
  keine automatische Löschung von Rückweg-Ordnern.
- Modul-`.previous/<id>`: genau eine Vorversion je Modul. Sie wird beim nächsten erfolgreichen Update des Moduls
  ersetzt und bei der Deinstallation entfernt.
- Die NAS-Sicherung (`b907dd0f`, Rest-Backup) ist davon getrennt. Diese Sicherungen sind nur für den Rückweg da und
  ersetzen kein Backup.

## 7. Etappen

Jede Etappe ist ein eigener PR mit Tests (Attrappen wie `tests/test_update_end_marker_linux.py`). Die Probe läuft
zuerst auf hydratest, dann auf .4, und auf dem Hauptserver nur mit Tills OK.

| Etappe | Inhalt | Nutzen allein | Abnahme |
|---|---|---|---|
| **U1** | Diese Spec | — | Freigabe durch Till |
| **U2** | Frontend-Bau in `dist.neu` + atomarer Tausch (Linux, Mac, `_frontend_build` der Module) | Ein Bau-Fehler lässt das laufende Frontend heil (Fall TS2307) | Test: Bau scheitert → `dist` unverändert |
| **U3** | Phase A: Sperre, `OLD_COMMIT`, Platzprüfung, `db_snapshot.py` (`VACUUM INTO` + `quick_check` + zstd), Config-, Unit- und dist-Sicherung, Aufbewahrung §6; **noch kein Rückweg** | Es gibt eine Sicherung, ein Rückweg ist von Hand möglich (Anleitung im Log) | Tests: wenig Platz → Abbruch vor `git pull`; Sicherung ist lesbar und `quick_check ok` |
| **U4** | Phase C (Health + Commit + Migrationsstand) und Phase D (automatischer Rückweg, `kaputt/`, Schlusszeile mit „zurückgesetzt“), E13 (unterbrochenes Update), Warnungs-Sammlung E10 | Ziel §1 für Linux erreicht | Tests mit Attrappen je Fehlerfall E4–E8, E12, E15; echte Probe auf hydratest mit absichtlich kaputtem Commit (Build-Fehler, kaputte Migration, Import-Fehler) |
| **U5** | Mac: `update-mac.sh` auf `hh_git_update`, Phase A/C/D mit Bordmitteln, plist-Umbau-Pfad mit Prüfung | Ziel §1 auf dem Mac | Attrappen-Tests `test_mac_update*.py`, Probe auf .186 |
| **U6** | Module: `.previous/<id>`, Bau-Rückweg, DB-Sicherung vor Modul-Updates, Cockpit-Knopf „alte Version zurückholen“ | Ziel §1.5 | Test: Modul-Bau scheitert → alter Modulstand + altes `dist`, kein Neustart |

Unabhängig davon als eigener Task: der Nebenbefund `47-samba.sh` `chown -R` auf die Workspaces (§2.1).

## 8. Entscheidungen (Till, 23.11.2026)

Alle Vorschläge F1–F10 angenommen. Die Fragen bleiben zur Nachvollziehbarkeit stehen.

- **F1 – Sicherungsformat:** `VACUUM INTO` + zstd (rund 25 s, 452 MB auf .4) statt `backup()` (63 s, 9,1 GB)?
  Vorschlag: ja. Nebeneffekt: Beim Rückweg ist die DB kompakt (1,8 statt 9,1 GB), weil die rund 80 % freien
  Seiten fehlen. Das ist harmlos, aber eine sichtbare Änderung.
- **F2 – Daten zwischen Sicherung und Rückweg:** Nachrichten, die während des Updates (typisch 1–5 min) im alten
  Dienst entstehen, landen beim Rückweg nur in `kaputt/sessions.db`. Reicht das? Alternative: Den Dienst ab der
  Sicherung in einen Nur-Lese-Modus schalten (aufwendig) oder die Sicherung erst direkt vor dem Neustart machen.
  Das wäre kürzer, aber dann gäbe es keinen Schutz vor Phase-B-Fehlern auf Konfigurationsdateien.
  Vorschlag: so lassen und im Log nennen.
- **F3 – venv:** immer sichern (rund 14 s und 670 MB je Lauf, unkomprimiert) oder nur, wenn sich Python bzw.
  `pyproject.toml` ändert (sonst `pip install -e` mit dem alten Commit)? Vorschlag: nur bei Änderung.
- **F4 – Modul-Migration scheitert beim Kern-Update:** Soll das den ganzen Kern zurückdrehen oder nur warnen
  (Modul nicht geladen, Rest läuft)? Vorschlag: nur warnen (E9).
- **F5 – Modul-Update nach dem Neustart kaputt:** automatisch auf `.previous` zurück (zweiter Neustart) oder nur
  per Knopf? Vorschlag: per Knopf, automatisch nur beim Bau-Fehler.
- **F6 – Unterbrochenes Update (E13):** Beim nächsten Dienststart automatisch zurückdrehen oder nur melden und per
  Knopf anbieten? Vorschlag: nur melden; automatisch nur, wenn der Dienst mit dem neuen Commit nicht startet.
- **F7 – Wartezeit Health:** 120 s genug? Die Startdauer auf .4 (Module, Mirror-Catch-up) ist nicht gemessen; sie
  wird in U4 auf hydratest/.4 gemessen und der Wert dann festgelegt. Vorschlag: 120 s, einstellbar.
- **F8 – Aufbewahrung:** die letzten 2 erfolgreichen Sicherungen, und Rückweg-Ordner nie automatisch löschen. Passt das?
- **F9 – apt-Vollupgrade (`hh_system_upgrade`):** Er läuft heute **vor** dem Frontend-Bau und lässt sich nicht
  zurückdrehen. Soll er ans Ende wandern (nach erfolgreicher Prüfung), damit ein Rückweg nie mit neuen Systempaketen
  und altem Code endet? Vorschlag: ja, als Teil von U4.
- **F10 – Hauptserver:** Die erste echte Probe auf dem Hauptserver erst nach U4 und mit einem absichtlich kaputten
  Test-Branch auf hydratest. Einverstanden?
