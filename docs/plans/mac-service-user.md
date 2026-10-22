# Plan: Eigener Dienst-Nutzer für HydraHive auf dem Mac (`_hydrahive`)

Status: **FREIGEGEBEN (Richtung)** – Till 22.10.2026: „ok mache a“. Dieser Plan: Umfang + Etappen zur Freigabe.
Task 6de37559, Teil von f4a303a9.

## Befund (MacBook Air M2, macOS 27.0.1, 22.10.2026)

Seit macOS 15 gilt der Datenschutz **„Lokales Netzwerk“** pro Benutzer (Apple TN3179). HydraHive läuft auf dem Mac als
**der Mac-Besitzer** (`HH_USER = whoami` beim Installieren). Ist dieser Nutzer am Bildschirm angemeldet – der
Normalfall –, behandelt macOS jeden Prozess dieses Kontos wie eine App des Nutzers, **auch als LaunchDaemon**.
Programme, die nicht von Apple signiert sind (Homebrew-Python, Node, …), bekommen ohne Abfrage
`OSError 65 No route to host` für jedes Ziel im lokalen Netz.

Prüf-LaunchDaemon, Verbindung zur Colima-VM (192.168.64.2) und ins LAN (192.168.178.4):

| läuft als | Programm | Ergebnis |
|---|---|---|
| `alexmo` (am Bildschirm angemeldet) | venv-/Homebrew-Python, Python.app, umsigniert, Node | ❌ 65 |
| `alexmo` | Apple `/usr/bin/python3`, `nc`, `curl` | ✅ |
| `root` | venv-Python | ✅ |
| `root` → `setuid(alexmo)` im Prozess | venv-Python | ❌ 65 |
| `nobody`, `_www` | **gleiches** venv-Python | ✅ |
| **neu angelegtes verstecktes Systemkonto (UID 450)** | **gleiches** venv-Python | ✅ |
| Intel .186 (macOS 15.3, niemand angemeldet) | venv-Python als `admin` | ✅ |

Eine Freigabe am Bildschirm („Python erlauben“) hilft **nicht** für den Daemon (getestet). Internet, Tailnet, Router
und localhost sind nicht betroffen.

**Folgen heute:** Container-Portfreigaben, Server-Kopplung im LAN, Home Assistant/Ollama/Mining-Rechner im LAN –
alles, was das Backend im Heimnetz anspricht, scheitert auf jedem Mac mit angemeldetem Besitzer.

## Ziel

Alle HydraHive-Dienste laufen unter einem eigenen, versteckten **System-Konto `_hydrahive`** (wie Linux `hydrahive`,
wie `_postgres`/`_www` bei macOS). Neue Installationen sofort, bestehende per **Update** (einmaliger Umzug).
Nebenbei sicherer: HydraHive kommt nicht mehr an die privaten Dateien des Mac-Besitzers.

## Kernentscheidungen

1. **Konto:** `_hydrahive`, UID/GID frei im Bereich 450–499 (Nutzer UND Gruppe frei prüfen – 400 ist auf macOS 27
   schon eine Gruppe), Shell `/usr/bin/false`, Home `/usr/local/var/hydrahive2/home` (eigener Ordner, Caches:
   pip, huggingface, npm), `IsHidden 1`. Anlegen per `dscl` (idempotent).
2. **Homebrew bleibt beim Mac-Besitzer.** brew verweigert root und gehört dem Menschen; `brew install` läuft weiter
   als Besitzer (`HH_BREW_USER` = wer installiert). `_hydrahive` **nutzt** nur die Programme (lesen/ausführen –
   getestet: ffmpeg, postgres, limactl laufen als Fremdkonto).
3. **Wem gehört was danach:**
   | Ort | Besitzer |
   |---|---|
   | `/opt/hydrahive2` (Repo, venv, frontend/dist) | `_hydrahive` |
   | `/opt/hydralink` | `_hydrahive` |
   | `/usr/local/var/hydrahive2` (Daten, sessions.db, Workspaces, colima, voice) | `_hydrahive` |
   | `/usr/local/etc/hydrahive2` (Secrets, Config) | `_hydrahive`, 0750/0600 |
   | `/usr/local/lib/hydrahive2/{containers,voice,tailscale}` | root (Programme, nur lesen) |
   | Logs `/usr/local/var/log/hydrahive2*`, `agentlink*` | `_hydrahive` |
   | Homebrew `/opt/homebrew` bzw. `/usr/local` | Mac-Besitzer (unverändert) |
4. **Dienste mit `UserName=_hydrahive`:** backend, agentlink, agentlink-frontend, voice-stt, voice-tts, colima.
   Unverändert root: nginx (Port 443), update, addon, restart, tailscaled.
5. **PostgreSQL:** Datenordner liegt heute in Homebrew (`/opt/homebrew/var/postgresql@16`, Besitzer Mac-Nutzer).
   → **Neuer Datenordner** `/usr/local/var/hydrahive2/postgres` (Besitzer `_hydrahive`), Dienst als `_hydrahive`.
   Umzug: `pg_dumpall` als alter Nutzer → `initdb` + Import als `_hydrahive`. (Homebrew-Ordner bleibt liegen, wird
   nicht gelöscht.) Superuser-Rolle `_hydrahive`.
6. **git:** Repo gehört `_hydrahive`; `update-mac.sh` ruft `git` als `_hydrahive` (wie heute als `HH_USER`).
   Für den Menschen im Terminal: Hinweis `sudo -u _hydrahive git …` in der Doku.
7. **Colima-VM:** Lima-Instanz gehört dem Konto, das sie startet. Umzug: VM stoppen, `COLIMA_HOME` umschreiben
   (`chown -R`), als `_hydrahive` starten. Lima braucht `$HOME` → eigenes Home (Punkt 1). Risiko: vz/Netz unter
   einem Konto ohne GUI-Sitzung – **früh testen** (Etappe 1).
8. **Umzug ist einmalig und reversibel:** Merker `HH_SERVICE_USER=_hydrahive` in install.conf. Vor dem Umzug
   Sicherung von etc + sessions.db + pg_dumpall nach `/usr/local/var/hydrahive2-backup-<datum>`. Bricht ein
   Schritt ab → alter Zustand bleibt lauffähig (Dienste erst am Ende umstellen).
9. **Linux unverändert.** Alles hinter `modules-mac/` bzw. `*-mac*`.

## Umsetzung: zwei Namen statt einem

Bisher steht `HH_USER` für zwei Dinge zugleich – **Besitzer von Homebrew** (brew verweigert root, muss als dieser
Nutzer laufen) und **Dienst-Nutzer** (Besitzer von Repo/Daten, `UserName` der Dienste). Das wird getrennt:

| Variable | Bedeutung | Mac neu | Mac bisher |
|---|---|---|---|
| `HH_BREW_USER` | ruft `brew` auf | Mac-Besitzer (Besitzer von `$(brew --prefix)`) | `HH_USER` |
| `HH_USER` | Dienst-Nutzer: Besitzer von Repo/Daten/Config, `UserName` der Dienste, `git`/`pip`/`npm` | `_hydrahive` | Mac-Besitzer |

So bleiben alle Stellen, die heute `HH_USER` für Besitz/Dienste nutzen, unverändert; nur die brew-Aufrufe
(`run_brew`, `00-deps.sh`, `48-postgres.sh`, `60-nginx.sh`, `mac-postgres-daemon.sh`, hydralink `mac-common.sh`)
nutzen künftig `HH_BREW_USER`. `HOME` der Dienste: Home des Kontos statt `/Users/$HH_USER`.

## Etappen

1. **Machbarkeit (Wegwerf, .223 + .186):** `_hydrahive` anlegen, Kopie von venv/Daten, Backend als `_hydrahive`
   starten (anderer Port), LAN/VM-Verbindung, Colima als `_hydrahive` starten, PostgreSQL-Datenordner als
   `_hydrahive`. Danach restlos entfernen. **Ergebnis an Till, bevor gebaut wird**, falls ein Punkt nicht geht.
2. **Neuinstallation:** `lib/mac-service-user.sh` (Konto anlegen), `install-mac.sh` + Module nutzen `HH_SVC_USER`
   für Besitz/Dienste und `HH_BREW_USER` für brew. Tests auf nachgebautem Mac (dscl/launchctl als Aufzeichnung).
3. **Umzug per Update:** `lib/mac-migrate-service-user.sh` (Sicherung → Dienste stoppen → chown → Postgres
   umziehen → Colima umziehen → plists neu → starten → Prüfung), aufgerufen aus `update-mac.sh`, wenn Merker fehlt.
4. **Abnahme:** M2 (.223, Umzug einer echten Installation mit Voice + Container) und Intel .186 (Umzug mit Tailscale
   ohne App): Portfreigabe von außen, Spracheingabe, Container, Neustart ohne Anmeldung, Update danach, Kopplung im
   LAN. Linux-Gegenprobe hydratest.
5. Doku `INSTALL-macOS(.de).md` (Terminal-Befehle mit `sudo -u _hydrahive`).

Etappen 2+3 können ein PR sein; Umfang grob 10–15 Dateien im Installer, Kern nur, wo `HH_USER` angenommen wird.

## Stand Etappe 2 (22.10.2026, Branch feat/mac-service-user)

Neuinstallation unter `_hydrahive` gebaut und live geprüft:

- Rollen-Helfer `installer/lib/mac-roles.sh`: `as_brew` (Homebrew-Besitzer), `as_svc` (Dienst-Konto, HOME = Konto-Home),
  `priv`, `hh_conf_get/hh_conf_set` (install.conf nur über sudo lesbar). Alter Weg (HH_USER = Mac-Besitzer):
  beide Rollen fallen zusammen, nichts ändert sich.
- PostgreSQL: eigener Datenordner `/usr/local/var/hydrahive2/postgres`, Superuser `_hydrahive`, psql über 127.0.0.1.
- Log-Ordner `/usr/local/var/log` wird nicht mehr übernommen (gehört auf Intel Homebrew) – das Konto bekommt per
  Zugriffsrecht (ACL) nur „Dateien anlegen“.
- AgentLink: hydralink bekommt `HL_BREW_USER` (hydralink-PR, Branch feat/mac-service-user).

Live (alte Installationen vorher gesichert nach `/usr/local/var/hh-alt-<nutzer>-2210`):

| | Intel .186 (macOS 15.3.1) | M2 .223 (macOS 27.0.1, Besitzer angemeldet) |
|---|---|---|
| Installation | 213 s, fehlerfrei | 701 s (VM-Abbild + Sprachmodell neu), fehlerfrei |
| Dienste als `_hydrahive` | backend, postgres, agentlink, colima, voice | ebenso |
| LAN aus dem Backend-Python | ✅ | ✅ (vorher FEHLER 65) |
| Container-Portfreigabe von außen | ✅ | ✅ (vorher kaputt) |
| Spracherkennung | ✅ 3 s | ✅ 3 s |
| Tailscale | ✅ (Anmeldung übernommen, Bediener `_hydrahive`) | – |
| Neustart ohne Anmeldung | ✅ alles wieder da | – |

Nebenbefund M2: Der erste Container nach frischer VM lädt das Abbild > 5 min → `incus_timeout`, Container bleibt als
Waise. Eigener Task (Zeitlimit beim ersten Abbild bzw. Aufräumen nach Zeitüberschreitung).

## Etappe 3: Umzug per Update (`installer/lib/mac-migrate-service-user.sh`)

Aufruf aus `update-mac.sh` (root) **nach** git pull/pip/Frontend, wenn `HH_SERVICE_USER` in install.conf fehlt.
Abschalten mit `HH_SERVICE_ACCOUNT=no` (in install.conf oder Umgebung) – dann bleibt alles wie bisher.

Schritte (jeder Schritt idempotent, Fortsetzung nach Abbruch möglich):
1. **Sicherung** nach `/usr/local/var/hydrahive2-backup-<datum>`: Config-Ordner, sessions.db (sqlite3 .backup),
   `pg_dumpall` (als alter Nutzer). Ohne Sicherung kein Umzug.
2. **Konto anlegen** (`mac-service-user.sh`).
3. **Dienste anhalten**: backend, agentlink(-frontend), voice-stt/-tts, colima (VM sauber stoppen als alter Nutzer).
   Tailscale, nginx, update, addon, restart laufen als root weiter.
4. **Besitz übertragen**: `/opt/hydrahive2`, `/opt/hydralink`, Daten-, Config-Ordner, `/usr/local/etc/hydralink`,
   Log-Dateien der Dienste (nicht der Ordner selbst – ACL wie 20-paths.sh), voice/stt+tts-Daten.
5. **PostgreSQL umziehen**: neuer Datenordner als `_hydrahive` (mac-postgres-daemon.sh), alte Datenbank auf Port 5433
   als alter Nutzer starten, `pg_dumpall` → Import in die neue (Rolle des alten Nutzers vorher anlegen, damit
   Eigentümer-Zeilen passen), alte anhalten. Homebrew-Ordner bleibt liegen.
6. **Dienst-Dateien neu**: 50-launchd (Backend, HOME), 55-launchd-triggers, mac-addon-trigger, 75-agentlink,
   70-containers/55-voice (wenn gewünscht), `tailscale set --operator=_hydrahive`.
7. **Prüfen**: Backend-Health, AgentLink-Health. Erst dann Merker `HH_SERVICE_USER=_hydrahive` setzen.

Fehlschlag in 3–6: Merker bleibt weg, Meldung im Update-Log samt Sicherungsort. Rückweg von Hand ist dokumentiert
(Sicherung zurück, plists des alten Nutzers neu schreiben mit `HH_USER=<alt> 50-launchd.sh`). Das Update selbst
(neuer Code) gilt trotzdem als erfolgreich.

Wichtig beim Umzug aus dem Update-Dienst: Der Update-Dienst selbst wird nicht entladen (XPC_SERVICE_NAME, #605).

## Stand Etappe 3 (22.10.2026)

`lib/mac-migrate-service-user.sh` (Ablauf), `lib/mac-pg-move.sh` (Datenbank), `lib/mac-migrate-rollback.sh` (Rückweg),
aufgerufen aus `update-mac.sh`. Live:

| | Intel .186 (Terminal-Update) | M2 .223 (Knopf im Cockpit, Besitzer angemeldet) |
|---|---|---|
| 1. Versuch | Abbruch beim Import (Sicherungsordner 0700 root, Konto durfte den Dump nicht lesen) → halber Zustand, von Hand repariert → **Rückweg gebaut** | Abbruch `initdb: invalid locale` (Update-Dienst ohne LANG) → **Rückweg griff**, alles lief weiter als alexmo |
| 2. Versuch | ✅ 2½ min, Daten vollständig (3 DBs, Chats, Container, Tailscale-Anmeldung) | ✅ ~1 min, Daten vollständig |
| danach | Neustart ohne Anmeldung ✅, Folge-Update ✅ (kein zweiter Umzug) | Heimnetz ✅, Portfreigabe von außen ✅, Spracherkennung ✅ |

## Nicht-Ziele
- Homebrew umziehen oder neu installieren.
- Tailscale-App-Anzeige (eigener Task 3fa604f4).

## Risiken
- Lima/vz unter einem Konto ohne GUI-Sitzung (Etappe 1 klärt).
- Bestehende Installationen mit eigenen Dateien im Workspace des Besitzers (Projekte, die auf `~/…` zeigen) →
  `_hydrahive` darf dort nicht lesen. Hinweis in der Doku; Mounts später.
- Update-Abbruch mitten im Umzug → Etappe 3 muss „halber Umzug“ erkennen und fortsetzen.
