# Plan: AgentLink (HydraLink) auf dem Mac

Status: **FREIGEGEBEN** (Till 21.10.2026: „ja das kannst du alles machen“) und **GEBAUT**, siehe §Umsetzung. Task f4a303a9 (Etappe 1 von 2; Etappe 2 = Container über Colima/Incus).

## Anlass

Erster echter Mac-Tester (Apple Silicon, seit 20.10.2026): Installation lief durch, Buddy geht, AgentLink ist
„nicht verbunden“. Till (21.10.): AgentLink soll auf dem Mac laufen, **auch zum Verbinden der Server untereinander**.

## Befunde (Code + Intel-Test-Mac .186, 21.10.2026)

1. `installer/install-mac.sh` hat **keine AgentLink-Phase**. Unter Linux macht das `installer/modules/75-agentlink.sh`
   (klont `hydralink` nach `/opt/hydralink`, ruft dessen `installer/install.sh`).
2. Der HydraLink-Installer ist reines Linux: `apt`, `systemd`, `useradd`, `sudo -u postgres`. Auf dem Mac nicht nutzbar.
3. Der Kern sucht AgentLink ohne Einstellung unter `http://127.0.0.1:9000` (`settings/_services.py`,
   `DEFAULT_AGENTLINK_URL`). Auf dem Mac läuft dort nichts → Dashboard „nicht verbunden“, `ask_agent` scheitert.
4. .186: `/opt/hydralink` fehlt, kein Redis. Vorhanden: Homebrew 5.1.8, python@3.12, node 25, postgresql@16 (als
   LaunchDaemon `io.hydrahive.postgres`), nginx 1.29 **mit** `http_auth_request_module`.
5. **Mac-nginx hinkt Linux hinterher** (`modules-mac/60-nginx.sh` vs. `modules/60-nginx.sh`). Es fehlen:
   - `/agentlink/`, `/agentlink/api/`, `/agentlink/ws` samt Anmeldeprüfung (`auth_request` gegen
     `/api/agentlink/dashboard-auth`),
   - `/api/peering/` **nur aus dem Tailnet** (100.64.0.0/10, fd7a:115c:a1e0::/48). Auf dem Mac geht `/api/peering/`
     heute über das allgemeine `/api/` **aus dem ganzen Netz** an das Backend (signiert, aber gegen die Spec
     `server-peering.md` §„nur Tailscale“),
   - Sicherheits-Kopfzeilen (CSP, HSTS, X-Frame-Options, nosniff, Referrer-, Permissions-Policy),
   - eigene, abgeschottete CSP für Modul-Ansichten `/api/module-device/<id>/sandbox/` (`module-view-sandbox.md`).
     Das einzige Modul mit Sandbox-Ansicht (Diagramme, `device_routes.py`) setzt die Sandbox-CSP bereits selbst
     („direkter Zugriff auf den Port, Mac“) → heute kein Loch, aber künftige Module verlassen sich auf nginx.
6. Kopplung braucht Tailscale. Der Kern sucht `tailscale` über `PATH`, sonst `/usr/bin/tailscale`
   (`tailscale/status.py`). Die Tailscale-App für macOS legt die Kommandozeile unter
   `/Applications/Tailscale.app/Contents/MacOS/Tailscale` ab, nicht im `PATH` des Dienstes.

## Ziel

Nach Install **oder** normalem Update auf dem Mac:
- AgentLink-Backend (Port 9000) + Dashboard (9001) laufen als LaunchDaemons, starten beim Hochfahren ohne Anmeldung.
- Dashboard „AgentLink verbunden“, `ask_agent` funktioniert, „Dashboard öffnen“ zeigt AgentLink unter `/agentlink/`.
- Server-Kopplung mit einem anderen HydraHive über Tailscale ist möglich (wie Linux).
- Mac-nginx hat dieselben Sicherheitsregeln wie Linux (Punkt 5).

## Aufbau

Gleiche Teilung wie unter Linux: HydraLink bringt seinen eigenen Mac-Installer mit, der Kern ruft ihn auf.

| Linux | Mac (neu) |
|---|---|
| `apt install redis-server`, systemd | **kein Redis** – `REDIS_URL=memory://` (Nachrichtenkanal im Prozess, siehe §Umsetzung) |
| eigenes PostgreSQL | **das vorhandene** `postgresql@16` des Kerns, eigene DB + Rolle `agentlink` |
| Systemnutzer `hydralink` | Dienstnutzer des Kerns (`HH_USER`), wie Backend und PostgreSQL auf dem Mac |
| `/etc/hydralink/agentlink.env` + `EnvironmentFile` | `$HL_CONFIG_DIR/agentlink.env` (0600) + Start-Wrapper (launchd kennt kein EnvironmentFile, wie `mac-backend-start.sh`) |
| `agentlink.service`, `agentlink-frontend.service` | LaunchDaemons `io.hydrahive.agentlink`, `io.hydrahive.agentlink-frontend` (`UserName=$HH_USER`, `RunAtLoad`, `KeepAlive`) |

Pfade: Code `/opt/hydralink` (wie `/opt/hydrahive2`), Konfiguration `/usr/local/etc/hydralink`, Logs
`/usr/local/var/log/agentlink*.log`. Python: Homebrew `python@3.12` oder neuer (gleiche Auswahl wie der Kern).
Apple Silicon (`/opt/homebrew`) und Intel (`/usr/local`) über `brew --prefix`, nie fest verdrahtet.

## Dateien

**Repo `hydralink`**
- `installer/install-mac.sh` – Einstieg (als Dienstnutzer, sudo nur für LaunchDaemons), ruft die Module der Reihe nach.
- `installer/modules-mac/00-deps.sh` – python@3.12/node über brew, prüft das PostgreSQL des Kerns (Redis entfallen, siehe §Umsetzung).
- `installer/modules-mac/10-postgres.sh` – Rolle + DB `agentlink` im vorhandenen postgresql@16; Passwort nur über stdin.
- `installer/modules-mac/20-agentlink.sh` – Code nach `/opt/hydralink/agentlink/backend`, venv, `agentlink.env`,
  Start-Wrapper `installer/lib/mac-agentlink-start.sh`, LaunchDaemon, Health-Wartezeit.
- `installer/modules-mac/30-frontend.sh` – Build mit `--base=/agentlink/`, LaunchDaemon mit `python3 -m http.server`.
- `tests/test_installer_mac.py` – Fake-Mac (Stubs für brew/sudo/launchctl/psql, wie `test_mac_postgres_daemon.py` im Kern).

**Repo `hydrahive2`**
- `installer/modules-mac/75-agentlink.sh` – klont/aktualisiert `/opt/hydralink` als Dienstnutzer, ruft `install-mac.sh`
  mit `HL_BACKEND_PORT=9000`, `HL_FRONTEND_PORT=9001`.
- `installer/install-mac.sh` – neue Phase „AgentLink“ (nach launchd, vor nginx; abschaltbar mit `HH_INSTALL_AGENTLINK=no`).
- `installer/update-mac.sh` – ruft `75-agentlink.sh` bei **jedem** Update (rüstet fehlendes AgentLink nach, aktualisiert
  vorhandenes). Fehlschlag beendet das Update nicht, wird aber deutlich gemeldet (wie Linux).
- `installer/modules-mac/60-nginx.sh` – Punkt 5 nachziehen; Marker wie unter Linux (`hh_agentlink_auth`,
  `hh_peering_tailnet`, `hh_module_sandbox`).
- `installer/update-mac.sh` – schreibt die nginx-Konfiguration neu, wenn ein Marker fehlt, und lädt nginx neu.
- `core/src/hydrahive/tailscale/status.py` – `_tailscale_bin()` findet zusätzlich die CLI der macOS-App.
- `docs/INSTALL-macOS(.de).md` – AgentLink + Kopplung beschreiben, Tabelle „Was auf dem Mac nicht geht“ anpassen.
- Tests: `core/tests/test_mac_agentlink.py`, Erweiterung `test_mac_update.py`, Test für `_tailscale_bin`.

## Reihenfolge (TDD, je Schritt rot → grün → Commit)

1. **hydralink: Voraussetzungen** – (ursprünglich Redis, entfallen) `00-deps.sh` installiert fehlendes python/node,
   bricht ohne PostgreSQL des Kerns ab; `memory://`-Kanal im Backend.
2. **hydralink: Datenbank** – Test: Rolle/DB werden angelegt, Passwort steht nie in einer Befehlszeile (nur stdin),
   Passwortdatei 0600, zweiter Lauf ändert nichts.
3. **hydralink: Backend** – Test: venv mit Python ≥ 3.12, `agentlink.env` 0600 + atomar, **kein Passwort in der plist**,
   plist startet über den Wrapper, Neubau des venv bei falschem Interpreter.
4. **hydralink: Frontend** – Test: Build mit `/agentlink/`-Pfaden, plist korrekt, nur 127.0.0.1.
5. **hydralink: install-mac.sh** – Test: Reihenfolge der Module, bricht auf Nicht-Mac ab.
6. **Kern: 75-agentlink.sh + install-mac.sh** – Test: Klonen/Pull als Dienstnutzer (nicht root, „dubious ownership“),
   Ports 9000/9001, Phase abschaltbar.
7. **Kern: update-mac.sh** – Test: ruft 75-agentlink.sh immer; Fehlschlag → deutliche Meldung, Update läuft weiter.
8. **Kern: Mac-nginx** – Test: alle Marker + Locations vorhanden, `/api/peering/` mit allow/deny, CSP vorhanden,
   Sandbox-CSP an der Modul-Ansicht; `update-mac.sh` schreibt bei fehlendem Marker neu. `nginx -t` auf .186.
9. **Kern: Tailscale-Pfad** – Test: `_tailscale_bin()` nimmt `PATH` → App-CLI (nur wenn vorhanden) → `/usr/bin/tailscale`.
10. **Doku** de + en.
11. **Abnahme auf .186 (Intel)**: Update über `deploy-mac.sh` auf dem Branch-Stand, dann Neustart des Macs
    (Dienste müssen ohne Anmeldung hochkommen), Dashboard „verbunden“, echter `ask_agent`-Handoff zwischen zwei
    Agenten, `/agentlink/` im Browser, `/api/peering/` aus dem LAN → 403.
12. **Kopplung**: .186 ↔ .2 über Tailscale koppeln (wenn Till Tailscale auf .186 möchte) oder mindestens prüfen,
    dass die Kopplungsseite den Mac-Server korrekt anzeigt.
13. Nach Merge: Tester macht ein normales Update → AgentLink kommt nach.

## Akzeptanzkriterien

- [x] Bestehende Installation bekommt AgentLink mit einem normalen Update (live .186). Frische Installation: Phase im
  Test mit Schein-Modulen geprüft, hydralink `install-mac.sh` als Nutzer live auf .186 – Kern-Neuinstallation nicht live.
- [x] Nach Neustart des Macs ohne Anmeldung: AgentLink und Dashboard laufen.
- [x] AgentLink verbunden (`/api/agentlink/status`), Handoff-Weg State → `handoff_received` live. `ask_agent` mit
  echtem Modell nicht live (Mac hat nur Master-Agenten, keinen Spezialisten als Ziel).
- [x] `/agentlink/` nur für angemeldete Admins; `/api/peering/` nur aus dem Tailnet.
- [x] Keine Passwörter in plists oder Befehlszeilen.
- [x] Linux-Installer unverändert; volle Kern-Suite + hydralink-Tests grün; Mutanten auf die neuen Prüfungen.

## Nicht in diesem Plan

- Container/Incus über Colima (Etappe 2, eigener Plan).
- SearXNG, Whisper, WhatsApp, Samba auf dem Mac.
- Tailscale automatisch installieren (Doku: App installieren, CLI aktivieren). Nur das Finden der CLI ist drin.
- Instanzname / AgentLink-ID je Server (Spec #517). Der Mac nutzt wie Linux die Standard-ID `hydrahive`.

## Umsetzung (21.10.2026)

**Abweichung vom Plan – kein Redis auf dem Mac.** Erster echter Lauf auf dem Intel-Test-Mac: Homebrew hat für
Redis (und Valkey) keine fertigen Intel-Pakete mehr und baute Redis samt LLVM und Rust aus dem Quellcode
(nach 6 Minuten abgebrochen). AgentLink nutzt Redis nur als Pub/Sub innerhalb **eines** uvicorn-Prozesses
(publish → Listener → WebSocket). Neu: `REDIS_URL=memory://` – gleiche Verteilung direkt im Prozess; Linux bleibt
bei Redis. `/health` meldet `"redis": "memory"`.

**Befund bei der Abnahme – brew unter root.** `update-mac.sh` läuft als root (LaunchDaemon). `sudo` setzt einen
eigenen PATH ohne Homebrew → „brew: command not found“ (AgentLink-Installation und nginx-Umbau scheiterten). Jetzt:
brew über den vollen Pfad (`/opt/homebrew/bin/brew` bzw. `/usr/local/bin/brew`), npm unter sudo mit PATH. Betraf auch
den bestehenden `mac-postgres-daemon.sh`.

**Zusätzlich:** nginx-Konfiguration wird vor der Übernahme mit `nginx -t` geprüft (sonst alte bleibt).

PRs: hydralink #7 (Mac-Installer + memory-Bus), hydrahive2.0 #595 (dieser Plan + Kern). Merge-Reihenfolge:
**hydralink #7 zuerst** (der Kern klont hydralink `main`).

Abnahme Intel-Test-Mac .186 (macOS 15.3.1, x86_64), Ausgangslage wie beim Tester (kein AgentLink):
- normales Update über den Update-Auslöser → AgentLink installiert, nginx neu, Kern neu gestartet ✓
- Neustart des Macs, **ohne Anmeldung** (`0 users`): alle 5 Dienste laufen, Kern meldet „AgentLink-WS verbunden“ ✓
- `/api/agentlink/status`: connected, ws_connected, backend_reachable ✓
- echter Handoff über AgentLink: State mit `handoff.to_agent` → `handoff_received` im Kanal `agent:<id>` ✓
- von außen: `/` 200, `/agentlink/` ohne Login 302, `/api/peering/…` aus dem LAN 403, CSP/HSTS/X-Frame/Permissions ✓
- Zugangsdaten nur in `/usr/local/etc/hydralink/*.env|password` (0600, Dienstnutzer), keine in plists ✓

**Offen – Kopplung über Tailscale:** Tailscale ist auf .186 nicht installiert. Der Tailscale-API-Schlüssel auf .2
(`/etc/hydrahive2/tailscale-admin.json`) ist abgelaufen (HTTP 401), daher kein Anmeldeschlüssel per API. Die
Tailscale-App braucht beim ersten Start eine Freigabe am Bildschirm (Systemerweiterung/VPN), das geht nicht per SSH.
Der Kern findet die CLI der App jetzt (`tailscale/_bin.py`); die echte Kopplung .186 ↔ .2 steht noch aus.
