# Plan: Tailscale auf dem Mac automatisch installieren

Status: **FREIGEGEBEN** (Till 21.10.2026: „ok mache es so“). Task 9fc3d0bb, Teil von f4a303a9 (Server-Kopplung).

## Befund (Intel-Test-Mac .186, 21.10.2026 – danach restlos entfernt)

- Tailscale-**App** (Download/App Store) verlangt beim ersten Start eine Freigabe am Bildschirm
  (Systemerweiterung bzw. VPN) → kein Installer kann das übernehmen.
- Offizielle dritte Variante (tailscale.com/kb/1065/macos-variants): **`tailscaled` ohne Oberfläche**, Kernel-utun,
  „Run before login: yes“, für unbeaufsichtigte Installationen gedacht. Lief als root ohne jede Freigabe;
  `tailscale up` lieferte sofort den Anmelde-Link.
- Fertige Mac-Dateien gibt es dafür nicht (GitHub-Release ohne darwin, Homebrew nur arm64). Selbst bauen:
  Go 1.27.3 (go.dev, feste SHA-256) + `go install tailscale.com/cmd/{tailscale,tailscaled}@v1.104.2` → **56 s** auf
  dem Intel-iMac, ohne Rückfragen.
- Einschränkungen der Variante: kein Exit-Node-Nutzen, Taildrop teilweise, kein Selbst-Update (→ unser Update),
  nicht parallel zur Tailscale-App.

## Ziel

Mac: Einstellungen → Zusatz-Module → **Tailscale → Installieren** (oder `install-mac.sh --with=tailscale`).
Danach auf der Tailscale-Karte **anmelden**: Anmelde-Link anklicken oder Auth-Key eintragen. Kopplung mit anderen
HydraHive-Servern wie unter Linux. Linux-Installer unangetastet.

## Bauteile

### Installer (nur Mac)
- **neu** `installer/modules-mac/80-tailscale.sh`
  - Ist `/Applications/Tailscale.app` vorhanden → **nichts installieren**, Hinweis ausgeben, Erfolg (der Kern findet
    die App-CLI schon, `tailscale/_bin.py`).
  - Go in fester Version mit **fester SHA-256** je Architektur in einen Wegwerf-Ordner laden.
  - `tailscale` + `tailscaled` in fester Version bauen (`GOTOOLCHAIN=local`, `GOFLAGS=-trimpath`, eigener
    GOPATH/GOCACHE im Wegwerf-Ordner), nach `/usr/local/lib/hydrahive2/tailscale/<version>/`, verlinkt nach
    `/usr/local/lib/hydrahive2/tailscale/bin`. Danach Go-Ordner löschen (Modul-Cache ist schreibgeschützt → vorher
    `chmod -R u+w`).
  - LaunchDaemon **`io.hydrahive.tailscaled`** (root – braucht utun), `RunAtLoad`, `KeepAlive`, Zustand in
    `/usr/local/var/hydrahive2/tailscale/tailscaled.state`, Socket Standard (`/var/run/tailscaled.socket`).
  - `tailscale set --operator=<Dienstnutzer>` → HydraHive darf `up`/`logout`/`status` ohne sudo.
  - `HH_INSTALL_TAILSCALE=yes` in `install.conf`.
  - Läuft die gewünschte Version schon → nicht neu bauen (Update schnell).
- `install-mac.sh`: Phase „Tailscale“ nur mit `--with=tailscale` / `HH_INSTALL_TAILSCALE=yes`.
- `update-mac.sh`: wenn gewünscht → `80-tailscale.sh` (neue Version bauen, Dienst neu laden).
- `lib/mac-addon-ctl.sh`: erlaubt zusätzlich `install tailscale`.
- `50-launchd.sh`: Backend-PATH um den Tailscale-bin-Ordner (wenn vorhanden).

### Kern
- `system/addons_status.py`: `MAC_INSTALLABLE = {"containers", "tailscale"}`.
- `tailscale/_bin.py`: eigener Mac-Ordner (`/usr/local/lib/hydrahive2/tailscale/bin/tailscale`) nach PATH, vor der App.
- `tailscale/control.py` + Route: **`POST /api/tailscale/login`** startet `tailscale up --timeout=…` **ohne** Auth-Key
  im Hintergrund und gibt die `AuthURL` zurück (die Status-Route liefert sie bereits als `auth_url`). Gilt auch für
  Linux – dort ist es ein zusätzlicher, optionaler Weg; der bestehende Auth-Key-Weg bleibt unverändert.

### Oberfläche
- Tailscale-Karte: im Zustand „nicht verbunden“ zusätzlich **„Im Browser anmelden“** → Link aus `auth_url` öffnen.
  Auth-Key-Formular bleibt.

### Doku
- `INSTALL-macOS(.de).md`: Tailscale-Abschnitt (App **oder** automatisch, nicht beides).

## Reihenfolge (TDD)
1. `80-tailscale.sh` auf nachgebautem Mac (falsche Go-Prüfsumme → Abbruch; App vorhanden → nichts tun; zweiter Lauf
   ohne Neubau; plist root/RunAtLoad; Operator gesetzt; install.conf).
2. install-mac/update-mac/mac-addon-ctl/50-launchd.
3. Kern: MAC_INSTALLABLE, _bin-Reihenfolge, Login-Route (rot → grün, Mutanten).
4. Oberfläche + i18n de/en, vitest.
5. Doku.
6. Abnahme .186: über das Cockpit installieren, Anmelde-Link erscheint, Till meldet an (oder Auth-Key), Neustart ohne
   Anmeldung → verbunden, `/api/peering/` aus dem Tailnet erreichbar, aus dem LAN 403; dann Kopplung .186 ↔ .2.
   Linux: hydratest-Update + Tailscale-Karte unverändert.

## Nicht in diesem Plan
- Exit-Node-Nutzung, Taildrop auf dem Mac.
- Automatische Anmeldung ohne Tills Zutun (braucht gültigen Tailscale-API-Schlüssel auf .2 – der ist abgelaufen).

## Umsetzung (21.10.2026)

- `modules-mac/80-tailscale.sh`, Option `--with=tailscale`, Cockpit (Zusatz-Module), Update pflegt mit, Backend-PATH.
- Version eingebrannt (`-ldflags` wie `build_dist.sh`), sonst meldet `tailscale version` „…-ERR-BuildInfo“.
- `POST /api/tailscale/login` + Karte „Im Browser anmelden“ (nur Links auf login.tailscale.com).
- **Befund:** `get_status()` stürzte vor der ersten Anmeldung ab (`TailscaleIPs: null` → „'NoneType' object is not
  iterable“) – die Karte zeigte dann keinen Anmelde-Link. Betraf **auch Linux**. Behoben + Test.

Abnahme .186: Update (mit Frontend-Build) ok, Tailscale über das Cockpit installiert (~2 min), Status `NeedsLogin` mit
Anmelde-Link, `/api/tailscale/login` liefert Link, Neustart ohne Anmeldung → `io.hydrahive.tailscaled` läuft.
hydratest (Linux): update.sh ok, Status `NeedsLogin` ohne Fehler, alle Zusatz-Module ohne Hinweis. Suite 4666 grün.
**Offen:** Anmeldung mit Tills Konto (Link öffnen), danach Kopplung .186 ↔ .2.

## Nachtrag 26.10.2026: App vorhanden → App hat Vorrang (Befund Berkan)

**Befund:** „Mit Browser anmelden“ meldete `internal_error`. Auf dem Mac lagen beide Varianten: HydraHives eigener
Build (mit Dienst `io.hydrahive.tailscaled`, inzwischen gestoppt) und die Tailscale-App, mit der Berkan angemeldet ist.
- `_bin.py` suchte PATH → eigener Build → App. Der Backend-PATH enthält den eigenen bin-Ordner, also wurde
  immer die tote eigene CLI gefragt („failed to connect to local Tailscale service“).
- `80-tailscale.sh` erkannte die App, beendete sich aber nur – eigener Dienst und Build blieben liegen.
- `login()` verwarf die Fehlerausgabe von `tailscale up`; ein Startfehler (OSError) wurde nicht abgefangen.

**Änderung:**
1. `_bin.py`: Ist die App-CLI da, wird **immer** sie genommen (vor PATH und eigenem Build). Ohne App wie bisher.
   Linux unverändert (dort gibt es den App-Pfad nicht).
2. `80-tailscale.sh`: App vorhanden **und** eigener Dienst eingerichtet → Dienst entladen, plist nach
   `<plist>.aus-wegen-app` umbenennen (rückholbar, nichts gelöscht), Hinweis ausgeben. Build-Ordner bleibt.
3. `login()`: Fehlerausgabe von `tailscale up` wird mitgelesen und im Fehlertext gemeldet; OSError beim Start →
   verständlicher Fehler (502) statt `internal_error`.

**Nicht getestet ohne echten Mac:** ob die App-CLI vom Dienst-Konto `_hydrahive` aus bedient werden darf (die
GUI-Variante verbindet sich mit der App des angemeldeten Nutzers). Abnahme durch Berkan nach dem Update.
