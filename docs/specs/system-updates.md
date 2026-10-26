# Systemupdates: das ganze System mit aktualisieren

Task f24c39bf. Auftrag Till, 26.10.2026: „Alles muss immer upgedatet werden … im Endeffekt immer das
komplette System updaten und nicht nur unsere Sachen.“ Anlass: PHP2Shell (CVE-2026-109618/-109619, CVSS 9.2).

## Befund

- `update.sh` aktualisiert nur HydraHive. Systempakete werden nur einzeln nachinstalliert, nie angehoben.
- Automatische Sicherheitsupdates (unattended-upgrades) hängen vom Zufall der Installation ab:
  - .2 und .4: an (Ubuntu-Standard, nur `-security`). Der PHP-Patch kam so am 22.10. auf .2.
  - hydratest (Ubuntu 24.04): nicht installiert, 225 Pakete veraltet.
- Hauptserver .2: 25 Pakete offen (systemd, qemu, gh …), `/run/reboot-required` seit 18.10. gesetzt.
  Niemand sieht das, die Admin-Konsole zeigt es nicht.
- Zusatzprogramme werden nur installiert, wenn sie fehlen. Eine ältere Version bleibt liegen:
  - dev-browser: .4 hat 0.2.7, Soll ist 0.2.9.
  - mmx-cli: .2 hat 1.0.28, hydratest 1.0.12 (ohne feste Version).
- Dienste mit alten Bibliotheken im Speicher werden nach einem Update nicht neu gestartet (needrestart fehlt).

## Ziel

1. **Jedes HydraHive-Update aktualisiert das ganze System:** alle Pakete, nicht nur die Sicherheitsupdates.
2. **Zwischen den Updates** spielt jeder Server Sicherheitsupdates nachts selbst ein.
3. **Dienste mit veralteten Bibliotheken** werden automatisch neu gestartet. Den Rechner startet HydraHive nie selbst neu.
4. **Zusatzprogramme mit fester Soll-Version** werden angehoben, wenn sie abweichen.
5. **Die Admin-Konsole zeigt** offene Systemupdates und ob ein Neustart des Rechners nötig ist.

## Umsetzung

### `installer/lib/system-upgrade.sh` (neu, wird gesourct, nie fatal)

`hh_ensure_auto_updates`
- Installiert `unattended-upgrades` und `needrestart`, wenn sie fehlen.
- Schreibt eigene Dateien, Ubuntu-Dateien bleiben unangetastet (wie `52hydrahive-tailscale`):
  - `/etc/apt/apt.conf.d/21hydrahive-auto-upgrades`: `Update-Package-Lists "1"`, `Unattended-Upgrade "1"`.
    Wird nach `20auto-upgrades` gelesen und gewinnt damit.
  - `/etc/needrestart/conf.d/50-hydrahive.conf`:
    - `$nrconf{restart} = 'a'`: automatisch neu starten, nie nachfragen.
    - `$nrconf{kernelhints} = 0` und `$nrconf{ucodehints} = 0`: keine Rückfragen.
    - Nie automatisch neu gestartet werden `hydrahive2*` und `hydra-voice-bridge`. Das Update startet sie
      am Ende ohnehin neu. Ein Neustart von `hydrahive2-update.service` würde das laufende Update abbrechen,
      ein nächtlicher Neustart von `hydrahive2` laufende Chats.
    - Ebenfalls nie: `incus*` und `containerd`. Docker, lxc und libvirt schließt needrestart schon selbst aus.
      Laufende Container und VMs sollen nicht nebenbei unterbrochen werden. Diese Dienste bekommen die neuen
      Bibliotheken beim nächsten Neustart des Rechners, den die Admin-Konsole anzeigt.
- Nachts bleibt es bei Sicherheitsupdates, dazu Tailscale. Alle Pakete kommen beim HydraHive-Update.

`hh_system_upgrade`
1. `dpkg --configure -a` (ein abgebrochener früherer Lauf blockiert sonst alles).
2. `apt-get update`.
3. `apt-get upgrade --with-new-pkgs -y` mit `DEBIAN_FRONTEND=noninteractive`, `--force-confdef`,
   `--force-confold` (geänderte Konfigurationen bleiben) und `DPkg::Lock::Timeout=600`
   (ein gerade laufender nächtlicher Lauf wird abgewartet).
   - `upgrade --with-new-pkgs` statt `full-upgrade`: neue Abhängigkeiten (z. B. neue Kernel) kommen mit,
     **entfernt wird nie etwas**.
4. Log: Anzahl aktualisierter Pakete, „Neustart des Rechners nötig“, wenn `/run/reboot-required` existiert.
   Wurden Grafiktreiber (`nvidia-*`, `libnvidia-*`) angehoben, schreibt das Update `/run/reboot-required`
   selbst. Der Treiber im Kernel passt bis zum Neustart nicht zur neuen Bibliothek.
5. Scheitert ein Schritt, bleibt es bei einer WARNUNG. Das HydraHive-Update läuft weiter.

Abschalten für Sonderfälle: `HH_SYSTEM_UPGRADE=no` in `install.conf`. Standard ist an.

**Stelle in `update.sh`:** direkt nach der Host-Selbstheilung (DNS muss gehen) und vor „Node.js prüfen“.
So ist ein angehobenes Node.js beim Frontend-Bau schon da.

### Zusatzprogramme anheben

- **`ensure_dev_browser`:** Weicht die installierte Version von `HH_DEV_BROWSER_VERSION` ab, wird sie per
  `npm install -g dev-browser@<Soll>` angehoben. Danach richtet `dev-browser install` die Laufzeit neu ein.
- **`installer/lib/mmx-cli.sh` (neu), `ensure_mmx_cli`:**
  - Feste Soll-Version `HH_MMX_VERSION=1.0.28`, die heute neueste und auf .2 im Einsatz.
  - Nur anheben, wenn mmx installiert ist. Neu installiert wird es weiter von `00-deps.sh` bzw. `55-voice.sh`.
  - `00-deps.sh` und `55-voice.sh` installieren künftig ebenfalls die Soll-Version.

### Admin-Konsole

- `GET /api/system/health` bekommt die Prüfung `system_updates` (`_system_updates.py`):
  - offen = Anzahl `Inst`-Zeilen aus `apt-get -s upgrade --with-new-pkgs` (läuft als Dienst-Nutzer,
    ohne Sperre), 15 Minuten zwischengespeichert;
  - Neustart nötig = `settings.reboot_required_file` (`/run/reboot-required`) existiert.
  - ok nur, wenn nichts offen ist und kein Neustart ansteht.
  - Ohne apt (Mac) fällt die Prüfung weg.
- Texte (de+en), ohne Terminal:
  - „System“
  - „aktuell“
  - „{{count}} Updates offen – kommen mit dem nächsten Update“
  - „Neustart des Rechners nötig“
  - „{{count}} Updates offen · Neustart nötig“
- Das Update-Fenster wartet höchstens 30 statt 10 Minuten. Viele Systempakete dauern länger.

## Nicht in diesem Schritt (eigene Tasks)

- Inhalte der Container (incus-LXC wie `hydrahive2-stt`, Docker-Images) aktualisieren.
- Mac (`update-mac.sh`, Homebrew).
- graphify (pip, ohne feste Version) anheben.
- PHP/MariaDB auf .2 und .4 entfernen: Betrieb, kein Code. Erst nach Sicherung.

## Tests

- `test_system_upgrade.py` mit Attrappen für apt-get, dpkg und needrestart, ohne Netz und ohne root:
  - Reihenfolge `dpkg --configure -a` → `update` → `upgrade --with-new-pkgs`, mit Schaltern ohne Rückfragen.
  - Kein `full-upgrade`/`dist-upgrade`/`autoremove`.
  - Fehlschlag ergibt nur eine WARNUNG, Rückgabe 0.
  - `HH_SYSTEM_UPGRADE=no` lässt apt in Ruhe.
  - Nvidia-Paket angehoben → Neustart-Marke wird gesetzt.
  - Konfigurationsdateien mit genau diesem Inhalt; idempotent.
  - unattended-upgrades/needrestart werden nur installiert, wenn sie fehlen.
- `update.sh`: Aufruf nach der Host-Selbstheilung und vor Node.js; Abschaltung über `install.conf`.
- dev-browser: 0.2.7 vorhanden → wird auf 0.2.9 angehoben, Laufzeit neu eingerichtet. Soll-Version → nichts passiert.
- mmx: alte Version → angehoben; fehlt → nichts; Soll-Version → nichts.
- Backend: Zählung, Neustart-Marke, Zwischenspeicher, ohne apt keine Prüfung.
- Frontend: HealthBar-Texte, Wartezeit 30 Minuten.
