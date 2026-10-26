# Plan: Projekt-Ordner auf dem Mac im Netz freigeben (wie Samba unter Linux)

> **Status:** Freigegeben (Till, 26.10.2026: „wir machen erst mal a, ja du darfst den Kern ändern solange es die
> Linux-Version nicht kaputt macht“)
> **Task:** 7b4e1a2d · **Variante a:** ein gemeinsames Freigabe-Konto (wie Linux heute). Variante b (eigene Zugänge je
> Mitarbeiter, für Linux und Mac) folgt als eigener Plan.

## 1. Problem

Ein Kunde kommt auf dem Mac nicht an seine Dateien. Die Workspaces liegen unter
`/usr/local/var/hydrahive2/workspaces/projects/<id>`; der Daten-Ordner gehört dem versteckten Dienst-Konto
`_hydrahive` und ist `750` (`installer/modules-mac/20-paths.sh`). Unter Linux gibt es dafür Samba (Zusatz-Modul +
Schalter je Projekt), auf dem Mac nicht (`MAC_INSTALLABLE` ohne `samba`). Shell-Zugang für Mitarbeiter ist **keine**
Lösung (Sicherheit). Ziel: Mitarbeiter öffnen den Projekt-Ordner im Finder/Explorer – ohne Shell, ohne sudo.

## 2. Lösung: macOS-eigene Dateifreigabe (SMB) statt Samba

macOS bringt einen SMB-Server mit (`smbd`, gesteuert über `sharing` und `launchctl`). Wir bauen **kein** Samba auf dem
Mac, sondern nutzen ihn:

1. **Zusatz-Modul „Dateifreigabe“ (Mac)** – derselbe Eintrag `samba` im Cockpit (Einstellungen → Zusatz-Module),
   auf dem Mac installierbar. Neues Skript `installer/modules-mac/47-filesharing.sh` (root, über
   `lib/mac-addon-ctl.sh`):
   - **Freigabe-Konto** `hhshare` anlegen: verstecktes macOS-Konto **ohne Login-Shell** (`/usr/bin/false`), ohne
     Heimordner, nur für SMB. Passwort zufällig (gleiche Datei wie Linux: `$HH_CONFIG_DIR/samba.password`,
     0600, Besitzer Dienst-Konto, damit das Cockpit es anzeigen kann).
   - Konto für SMB freischalten (`pwpolicy`/`dscl`: SMB-Passwort-Hash), **keine** Anmeldung am Mac möglich
     (`IsHidden`, Shell `/usr/bin/false`, nicht in Gruppe `staff`).
   - **Rechte** über ACL statt Gruppen-Umbau: `hhshare` darf den Weg bis `workspaces/projects` nur **durchgehen**
     (`search`), auf jedem Projekt-Workspace **lesen und schreiben** (vererbbare ACL `file_inherit,directory_inherit`).
     Linux-artiges `chown -R`/`chmod 2775` wird **nicht** gemacht (Lehre aus dem Umzug .2 → .226).
   - SMB-Dienst einschalten (`launchctl enable system/com.apple.smbd`, `launchctl kickstart`).
   - Ordner für die Freigabe-Zustände: `$HH_CONFIG_DIR/mac-shares.d/` (Dienst-Konto darf schreiben).
2. **Freigabe je Projekt** (Schalter im Projekt wie Linux):
   - Backend schreibt eine **Anfrage-Datei** `mac-shares.d/<id>.want` (Name, Pfad aus `workspace_path`, ja/nein).
     Das Backend läuft als `_hydrahive` und darf `sharing` nicht (braucht root).
   - Ein LaunchDaemon `io.hydrahive.shares` (root, `WatchPaths` auf `mac-shares.d`) führt
     `installer/lib/mac-shares-ctl.sh` aus: liest **nur** die Anfrage-Dateien, prüft Name (`[A-Za-z0-9_-]{1,50}`) und
     Pfad (muss genau `$HH_DATA_DIR/workspaces/projects/<id>` sein, `<id>` nur `[A-Za-z0-9_-]`), dann
     `sharing -a <pfad> -S <name> -s 001 -g 000` bzw. `sharing -r <name>`, setzt die ACL für `hhshare` auf den
     Projektordner und schreibt `<id>.state` (`on`/`off`/`error:<grund>`).
   - Gleiches Muster wie `mac-addon-ctl.sh` (Anfrage-Datei → root-Daemon), keine Parameter aus der Oberfläche in Shell.
3. **Kern-Code** (`hydrahive/samba/`):
   - `manager.py` bekommt einen Mac-Zweig hinter `is_mac()`: `enable_share`/`disable_share`/`is_share_enabled`
     schreiben/lesen die Anfrage- bzw. Zustandsdateien statt `smb.conf`-Schnipsel; `samba_status()` meldet auf dem Mac
     „installiert“, wenn das Freigabe-Konto existiert und SMB läuft. **Linux-Pfad bleibt Zeile für Zeile unverändert.**
   - Mac-Teil in eigener Datei `samba/_mac.py` (Dateigröße, klare Trennung).
   - `addons_status.MAC_INSTALLABLE` + `samba`; `mac-addon-ctl.sh` erlaubt `install samba` → `47-filesharing.sh`.
4. **Oberfläche:** Projekt-Einstellungen zeigen auf dem Mac die Adresse als `smb://<host>/<freigabe>` (Finder) **und**
   `\\<host>\<freigabe>` (Windows); Benutzer/Passwort wie bisher. Hinweis-Text: „Im Finder: Gehe zu → Mit Server
   verbinden“. Linux unverändert (nur `\\…`; `smb://` ergänzend auch dort sinnvoll – ändert nichts Bestehendes).
5. **Doku:** `docs/INSTALL-macOS(.de).md` Abschnitt „Wo liegen meine Dateien? – Projekt im Netz freigeben“.

## 3. Sicherheit

- Kein Shell-Zugang für Mitarbeiter; das Freigabe-Konto kann sich am Mac nicht anmelden.
- Freigegeben wird **nur**, was im Cockpit pro Projekt eingeschaltet ist (Standard aus), nie der ganze Daten-Ordner,
  nie `master/`, `specialists/`, Einstellungen, Datenbank.
- root-Teil nimmt nur feste, geprüfte Werte aus Dateien im Config-Ordner (nicht beschreibbar für Mitarbeiter).
- Passwort nur in `samba.password` (0600), sichtbar nur für Projekt-Mitglieder mit Leserecht (wie Linux heute).
- Variante a: ein Konto für alle freigegebenen Projekte (bekannte Schwäche, gilt heute auch für Linux) → Variante b.
- Gastzugang aus (`-g 000`).

## 4. Tests (TDD, nachgebauter Mac wie `test_mac_voice_installer.py`)

- `47-filesharing.sh`: legt Konto ohne Shell an, setzt SMB-Passwort, ACL nur `search` auf dem Weg, schaltet smbd
  ein; idempotent (zweiter Lauf ändert nichts); kein `chown -R`.
- `mac-shares-ctl.sh`: gültige Anfrage → `sharing -a` mit richtigem Pfad/Namen + ACL + Zustand `on`; Aus → `sharing -r`;
  böse Namen/Pfade (`..`, `/`, Leerzeichen, fremder Ordner, Symlink) → abgelehnt, nichts ausgeführt;
  Bash 3.2 (`test_mac_bash32.py`).
- Kern: Mac-Zweig von enable/disable/is_enabled/status (Anfrage/Zustand), Linux-Tests unverändert grün, Mac-Addon
  erlaubt `samba`, API `projects/<id>/samba` auf dem Mac.
- Oberfläche: `smb://`-Adresse auf dem Mac.
- **Live:** Test-Mac (.186 oder M2): Zusatz-Modul installieren, Projekt freigeben, von einem anderen Rechner im Finder
  und Explorer verbinden, Datei anlegen → im Cockpit sichtbar; im Cockpit anlegen → im Finder sichtbar; Freigabe aus →
  Verbindung weg. Gegenprobe Linux (hydratest): Samba unverändert.

## 5. Offen / zu prüfen am echten Mac
- Genaue Befehle für das SMB-Passwort des Freigabe-Kontos ohne Login (`dscl … AuthenticationAuthority`/`pwpolicy`)
  und ob `sharing` auf macOS 15/26/27 noch so heißt – vor dem Bauen auf dem Test-Mac ausprobieren.
- Verbindet sich der Mac-Besitzer am **selben** Mac über `smb://localhost`? (macOS blockiert das teils) – sonst
  Hinweis in der Doku: im Finder unter „Netzwerk“ bzw. per Adresse des Macs.

## 6. Nicht in diesem Plan
- Variante b (eigene Zugänge je Mitarbeiter, nur eigene Projekte) – eigener Plan, Linux + Mac.
- ZIP-Download im Cockpit (eigener Task).
