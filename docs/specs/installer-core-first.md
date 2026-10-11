# Spec: Installer – erst der Kern, Zusatz-Module später über die Oberfläche

Status: ENTWURF (wartet auf Tills OK)
Datum: 2026-10-11 · Task a594de49

## Was

`install.sh` installiert ohne Rückfragen einen **funktionierenden Kern**: Backend, Oberfläche, nginx und HydraLink.
Alle anderen Bausteine werden danach im Admin-Cockpit unter **System → Zusatz-Module** mit je einem Knopf und einer
Log-Anzeige nachinstalliert. Das betrifft PostgreSQL, Container (incus), VMs, Samba, WhatsApp, Voice, Tailscale und
Local Media.

## Warum

Till, 11.10.: „den Installer eventuell mal ändern und die nötigen Module hardcoden und den Rest später über die GUI
nachinstallieren. Dann haben wir wenigstens schon mal ein funktionierendes LLM, was helfen kann.“

Anlass war eine WSL-Installation. Der User hatte alle Fragen mit „J“ beantwortet. apt brach dann mitten im Herunterladen
mit `Temporary failure resolving 'archive.ubuntu.com'` ab: Das DNS von WSL hatte kurze Aussetzer. Mit einem Aufruf ganz
ohne Zusatz-Module lief die Installation durch.

Je mehr Pakete der Erstlauf lädt, desto eher reißt er ab. Danach steht gar nichts, auch kein Chat, der beim Reparieren
helfen könnte.

## Ist (main 2487f467)

| Baustein | Modul | Frage im Installer | In der Oberfläche nachinstallierbar? | Pflege in `update.sh` |
|---|---|---|---|---|
| Kern (Python, Frontend, systemd) | 00/10/20/30/40/50 | – | – | immer |
| nginx | 60 | ja, Standard J | nein | wenn installiert |
| HydraLink | 75 | nein (Pflicht) | – | immer |
| Tailscale | 80 | ja, J | **ja** (`/api/tailscale/install`, `sudo -n bash`) | wenn `HH_INSTALL_TAILSCALE` ≠ no |
| PostgreSQL | 48 | ja, J | nein | wenn ≠ no |
| Voice | 55 | ja, J | **ja** (Trigger `.voice_install_request` + Log) | prüft Zustand, ohne Schalter |
| Container (incus) | 70 | ja, J | nein | prüft Zustand, ohne Schalter |
| VMs | 65 | ja, J | nein | prüft Zustand, ohne Schalter |
| Samba | 47 | ja, J | **ja** (Trigger `.samba_setup_request` + Log, SambaCard) | Self-Heal smb.conf |
| WhatsApp-Bridge | 45 | ja, J | nein | `npm install`, wenn die Bridge im Repo liegt |
| Local Media | 72 | ja, N | **ja** (Trigger mit Wort install/uninstall, Marker) | wenn Marker vorhanden |

Wichtige Befunde:
- Das Backend lauscht nur auf `127.0.0.1:8001`; die Oberfläche kommt über nginx. **Ohne nginx ist im Browser nichts zu
  erreichen.** nginx gehört deshalb zum Kern.
- `update.sh` installiert **VMs, Container und Voice nach, sobald sie fehlen** (Zustandsprüfung ohne Blick auf
  install.conf). Ein bewusst abgewähltes Modul käme beim nächsten Update also doch wieder. Das muss sich ändern, sonst
  hat „erst der Kern“ keinen Bestand.
- Die Nachinstallation läuft heute auf zwei Wegen: Trigger-Datei + systemd-Runner (Voice, Samba, Local Media,
  Bridge, Update) oder `sudo -n bash` direkt aus dem Backend (Tailscale). Die Trigger-Datei ist der robustere Weg: Er
  überlebt einen Neustart des Dienstes, hat ein eigenes Log und läuft getrennt vom Backend-Prozess.
- `65-vms.sh` und `70-containers.sh` patchen `hydrahive2.service` (Gruppen kvm/incus-admin, DeviceAllow) und starten
  den Dienst neu. Eine Nachinstallation aus der Oberfläche beendet also kurz das laufende Backend.

## Soll

### 1. Installer
- **Kern ohne Fragen:** 00, 10, 20, 30, 40, 50, 60 (nginx), 75 (HydraLink), dazu die vorhandenen Helfer (llmfit,
  graphify).
- **Zusatz-Module standardmäßig aus.** Neue Installationen schreiben für alle Module `no` in install.conf.
  Der Komponenten-Wizard entfällt im Normalfall.
- **Wer beim Installieren doch etwas mitnehmen will:**
  - `--with=postgres,voice,…` oder die bisherigen ENV-Variablen (`HH_INSTALL_VOICE=yes` …) wirken wie heute.
  - `--all` = bisheriges Verhalten (alles außer Local Media).
  - `--reconfigure` fragt wie bisher alle Module ab.
- **Bestands-Installationen:** Liegt install.conf schon vor, gilt sie unverändert. Ein Re-Run oder Update entfernt
  nichts und schaltet nichts ab.
- **Abschlussübersicht:** Hinweis „Zusatz-Module: Admin-Cockpit → System → Zusatz-Module“. Unter WSL zusätzlich der
  Hinweis, dass VMs, Container und Voice dort meist nicht laufen.
- **apt robuster:** Eine Datei `/etc/apt/apt.conf.d/80hydrahive-retries` mit `Acquire::Retries "5";` wird vor dem
  ersten `apt-get update` angelegt. **Kein** `ForceIPv4` (das wäre ein Eingriff ins Netz).
- **Vorab-Prüfung Netz/DNS** vor Phase 1: `getent hosts archive.ubuntu.com` und `github.com`. Schlägt sie fehl,
  bricht der Installer mit einer klaren Meldung ab. Unter WSL (erkannt an `/proc/sys/fs/binfmt_misc/WSLInterop` bzw.
  `microsoft` in `/proc/version`) nennt die Meldung die Schritte aus der README (`wsl --shutdown`, `dnsTunneling`).
  Nichts wird automatisch umgestellt.

### 2. Modul-Status ist die Wahrheit für `update.sh`
- In install.conf steht je Modul `yes` oder `no`. **`update.sh` pflegt nur Module mit `yes`.** Das gilt auch für VMs,
  Container und Voice; deren Zustandsprüfungen bekommen dieselbe Bedingung wie heute schon PostgreSQL und Tailscale.
- **Migration für Bestands-Installationen ohne Eintrag:** Fehlt ein Wert, wird er beim ersten Update aus dem Zustand
  abgeleitet. Ist das Modul installiert, wird `yes` gesetzt; sonst gilt der bisherige Standard (`yes`, damit sich für
  bestehende Server nichts ändert). Nur neue Installationen schreiben `no`.
- Local Media behält seinen Marker `local-media.enabled` und wird von der Migration nicht angefasst.

### 3. Nachinstallieren in der Oberfläche
- **Ein gemeinsamer Runner** `installer/addon-ctl.sh` (root, über `hydrahive2-addon.service` und Timer, wie Local Media):
  - Die Trigger-Datei `$HH_DATA_DIR/.addon_request` enthält genau eine Zeile `install <modul>`. Erlaubt sind nur die
    festen Modulnamen aus einer Liste im Skript (`postgres containers vms samba whatsapp voice tailscale`).
    Alles andere wird verworfen.
  - Der Runner setzt `HH_INSTALL_<MODUL>=yes`, ruft das Modul-Skript auf und schreibt **nur bei Erfolg** `yes` in
    install.conf (kleine Funktion, die genau eine Zeile ersetzt).
  - Abhängigkeiten: `voice` zieht vorher `containers` nach (wie heute im Wizard).
  - Die Trigger-Datei bleibt bis zum Ende liegen; die API meldet so „läuft“ und lehnt einen zweiten Auftrag mit 409
    ab. Das Log liegt in `/var/log/hydrahive2-addon.log`.
  - Module, die den Dienst neu starten (VMs, Container): Der Runner läuft getrennt vom Backend. Die Oberfläche zeigt
    vorher „HydraHive startet dabei kurz neu“ und liest das Log nach dem Neustart weiter.
- **Bestehende Wege bleiben bestehen und werden angeglichen:**
  - Voice und Samba gehen künftig über denselben Runner. Die alten Trigger bleiben eine Version lang als Umleitung,
    damit offene Oberflächen nicht brechen.
  - Tailscale wechselt von `sudo -n bash` im Backend auf den Runner.
  - Local Media bleibt wie es ist (eigene Prüfungen: GPU, VRAM, Platz).
- **API** (nur Admin, neues Modul `api/routes/system_addons.py`):
  - `GET /api/system/addons` liefert je Modul: `id`, `installed` (Zustandsprüfung), `enabled` (install.conf),
    `running`, `restarts_service`, `hint` (z. B. „unter WSL meist nicht verfügbar“).
  - `POST /api/system/addons/{id}/install` → 202, 409 bei laufendem Auftrag, 400 bei unbekanntem Modul.
  - `GET /api/system/addons/log?tail=` liefert das Log.
- **Zustandsprüfung je Modul** (lesend, ohne root):

  | Modul | Prüfung |
  |---|---|
  | postgres | `settings.pg_mirror_dsn` gesetzt |
  | containers | `incus_client.is_available()` |
  | vms | `qemu-system-x86_64` vorhanden **und** `/dev/kvm` lesbar |
  | samba | `samba_status()` |
  | whatsapp | `node_modules` der Bridge vorhanden |
  | voice | STT-Port `127.0.0.1:10300` erreichbar |
  | tailscale | `tailscale` vorhanden |
- **Oberfläche:** Im Admin-Cockpit → System eine Karte „Zusatz-Module“ mit einer Zeile je Modul:
  - Name, kurzer Nutzen, Status (installiert / nicht installiert / läuft).
  - Knopf „Installieren“ mit Rückfrage; bei VMs und Containern mit Hinweis auf den kurzen Neustart.
  - Ausklappbares Log wie bei Samba.
  - Der Knopf „Voice installieren“ im Kopf des System-Fensters entfällt zugunsten der Karte.

### 4. Doku
- README (de/en) im Abschnitt Windows/WSL:
  - `sudo bash installer/install.sh` reicht.
  - Zusatz-Module danach im Cockpit.
  - Ein Abschnitt „Keine Namensauflösung unter WSL“ mit den geprüften Schritten.
- `installer/README.md`: neue Schalter (`--with`, `--all`).

## Nicht in dieser Etappe
- Module **entfernen** über die Oberfläche (außer Local Media, das kann es schon). Deinstallieren berührt Daten
  (PostgreSQL, Container, VMs) und braucht eine eigene Spec.
- Automatische DNS-Reparatur unter WSL.
- macOS-Installer (`install-mac.sh`).

## Risiken
- **update.sh-Migration:** Wird `installed` falsch erkannt, würde ein Update ein Modul nicht mehr pflegen. Deshalb gilt
  im Zweifel `yes` (bisheriges Verhalten). Getestet wird mit einer Bestands-Installation auf hydratest, auf der alles
  installiert ist.
- **Neustart mitten in der Nachinstallation (VMs/Container):** Der Runner ist ein eigener systemd-Oneshot und läuft
  weiter. Getestet wird das im Browser.
- **Sicherheit:** Der Runner nimmt nur feste Modulnamen an. Die API ist nur für Admins. Es kommen keine neuen
  sudo-Rechte dazu; der Weg ist derselbe wie bei Local Media. Tailscale verliert seinen `sudo -n bash`-Aufruf aus dem
  Backend, was die Angriffsfläche eher verkleinert.

## Akzeptanz
1. Frische Installation (hydratest-Klon, Ubuntu 26.04) mit `sudo bash installer/install.sh`: keine Rückfragen,
   Oberfläche erreichbar, Login geht, ein LLM-Zugang lässt sich eintragen und der Chat antwortet. install.conf hat für
   alle Zusatz-Module `no`. `update.sh` danach installiert **nichts** nach.
2. Im Cockpit „Zusatz-Module“: PostgreSQL, Container, Samba und WhatsApp nacheinander installieren. Der Status springt
   auf „installiert“, install.conf auf `yes`, das Log ist lesbar. Ein zweiter Klick während eines Laufs ergibt 409.
3. VMs installieren: Der Dienst startet kurz neu, die Oberfläche zeigt danach Log und Status richtig.
4. Bestands-Installation (hydratest wie heute, alles installiert): `update.sh` installiert alles weiter, nichts wird
   abgeschaltet; install.conf bekommt fehlende Werte als `yes`.
5. `--all` und `HH_INSTALL_VOICE=yes` verhalten sich wie bisher.
6. DNS-Vorabprüfung: Mit absichtlich kaputtem `/etc/resolv.conf` bricht der Installer vor Phase 1 mit klarer Meldung
   ab; die WSL-Variante lässt sich über eine Test-Umgebungsvariable prüfen.
7. Tests:
   - Python für die API (Statusprüfungen gemockt, Runner-Trigger, 409, unbekanntes Modul).
   - Shell-Verhalten wie in `core/tests/test_host_selfheal.py`: echtes `bash` gegen ein tmp-Verzeichnis, mit Pfaden
     als Umgebungsvariablen. Geprüft werden `addon-ctl.sh` (Positivliste, install.conf nur bei Erfolg) und die
     install.conf-Migration. Statische Prüfungen von `install.sh` wie in `core/tests/test_install_sh_local_media.py`.
   - vitest für die Karte.
   - Browser-Test auf hydratest über genau den Klickweg aus dieser Spec.

## Offene Fragen an Till
1. **nginx fest im Kern?** Ohne nginx ist die Oberfläche nicht erreichbar. Vorschlag: ja, ohne Frage.
2. **PostgreSQL** (Datamining-Spiegel) auch erst später? Ohne PostgreSQL fehlt die Volltext- und semantische Suche im
   Gedächtnis; Chat und Agenten laufen trotzdem. Vorschlag: später über die Oberfläche.
3. **Tailscale-Weg angleichen** (vom Backend-`sudo` auf den Runner): jetzt mitmachen oder getrennt?
4. **Reihenfolge:** zuerst Installer + update.sh (Schritte 1, 2, 4) als eigener PR, danach die Oberfläche (Schritt 3)?
   Der erste Teil allein hilft schon bei Neuinstallationen. Für das Nachinstallieren wäre bis zum zweiten PR noch
   `--reconfigure` nötig.
