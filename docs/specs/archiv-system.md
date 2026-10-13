# Archiv- und Sicherungsspeicher (systemweit)

Task 58c680df. Stand 13.10.2026. **Entwurf, Design-Phase.**

## Wunsch (Till, 13.10.)

> Wir brauchen einen Backup- und Archivpfad auf einem externen Server, den ich
> irgendwo eintragen kann. Alle Daten sollten vor dem Löschen dorthin verschoben
> werden. Vielleicht ein systemweites Archivsystem, dorthin könnte man auch
> Projekt-Backups verschieben, wenn sie archiviert werden sollen. So verlieren
> wir keinerlei Daten und könnten das Archiv auch als gespeichertes Wissen
> nutzen und eventuell frühere Sachen wieder benutzen. In den Einstellungen den
> Backup-Server-Pfad und die Zugangsdaten eingeben, und JEDER Agent und jedes
> System kann dort Backups ablegen oder Daten archivieren.

## Problem

1. Löschen vernichtet Daten. `agent_config.delete()` entfernt `agents/<id>/` samt
   Gedächtnis endgültig (Prod: `agents/` 281 MB). Der Arbeitsordner bleibt
   verwaist liegen (Prod: 30 Waisen, hydratest: 343). `projects/config.delete()`
   löscht den Projekt-Arbeitsordner endgültig.
2. Es gibt keinen festen Ort für Sicherungen. Das System-Backup ist nur ein
   Browser-Download. Das NAS ist lediglich als Laufwerk im DEV-Projekt eingehängt.
3. Was einmal weg ist, kann kein Agent mehr finden oder wiederverwenden.

## Was es schon gibt (wiederverwendbar)

| Baustein | Wo | Brauchbar für |
|---|---|---|
| CIFS-Einhängen, Passwort nie in `ps` | `smbmounts/mounter.py` | Speicher einhängen |
| Zugangsdaten verschlüsselt (Typ `basic`) | `credentials/store.py` | NAS-Login |
| Wiedereinhängen beim Start | `smbmounts/reconcile.py` | nach Neustart |
| System-Backup als tar.gz | `backup/archive.py` | Backup aufs NAS statt Download |
| Nutzer-Export (DSGVO) | `backup/user_archive.py` | Muster für Agent-/Projekt-Pakete |
| Projekt-Status `archived` | `projects/_validation.py` | gibt es, tut aber nichts (Prod: 19 × `active`) |
| GUI-Einstellungen | `settings/editable.py` | Pfad und Zugang eintragen |
| Datamining-Suche (Volltext + Vektor) | `db/_mirror_*` | Archiv durchsuchbar machen |

## Randbedingungen

- **Daten dürfen nie verloren gehen.** Erst sicher am Ziel, dann am alten Ort weg.
  Ist das Archiv nicht erreichbar, wird **nicht gelöscht** (Fehler mit Grund).
- **Zugangsdaten nur im Credential-Speicher**, nie in Config oder Log.
- **CIFS kann keine Symlinks** (`nounix`), Agent-Ordner enthalten aber welche
  (z. B. `master/<id>/projects/…`). Darum wird gepackt (tar.gz) und nicht als
  Ordnerbaum kopiert.
- **Nicht nur NAS:** Eintragbar sein sollen auch ein lokaler Pfad (Test,
  Rechner ohne NAS) und später andere Ziele.
- **Agenten dürfen nicht beliebig in fremde Archive greifen.** Rechte wie beim
  Rest (Besitzer bzw. Projektmitglied, Admin sieht alles).

## Optionen

### A: NAS als Systemlaufwerk + Archiv-Ordnerbaum

Admin trägt in den Einstellungen Server, Freigabe, Unterordner und Zugangsdaten
ein. HydraHive hängt den Speicher systemweit ein (`$HH_DATA_DIR/archive-mount`).
Archivieren bedeutet: als tar.gz plus `archiv.json` dorthin schreiben.
- Vorteil: baut auf dem vorhandenen Mount-Code auf, klein, schnell fertig.
- Nachteil: bindet sich an CIFS. Ohne eingehängtes Laufwerk gibt es kein Archiv.
  Suchen nur über Dateinamen und `archiv.json`.

### B: Archiv-Dienst mit austauschbarem Speicher und Katalog

Wie A, aber dazwischen eine kleine Schicht `archive/`:
- **Speicher-Treiber:** `local` (Pfad) und `smb` (NAS). Weitere wie SFTP/S3
  kommen später dazu, ohne dass die Aufrufer sich ändern.
- **Katalog** in der Datenbank: ein Eintrag je Archivstück mit Art (`agent`,
  `project`, `system_backup`, `upload`), Name, Herkunft, Besitzer, Zeitpunkt,
  Grund, Größe und Prüfsumme. Damit lässt sich listen, filtern und
  wiederherstellen, ohne das NAS zu durchsuchen.
- **Eine API** für alle: Agent löschen, Projekt archivieren, System-Backup,
  Agent-Werkzeug `archive_put` / `archive_list` / `archive_get`.
- Optional (eigene Etappe): Textinhalte ins Datamining einspielen und als
  „Wissen“ durchsuchbar machen.
- Vorteil: Erfüllt den ganzen Wunsch („jeder Agent, jedes System“). Ziel
  austauschbar. Suchen und Wiederherstellen ohne NAS-Durchsuchen.
- Nachteil: deutlich größer, mehrere Etappen.

### C: Nur das System-Backup aufs NAS, Löschen wird Papierkorb

Gelöschtes wandert lokal in einen Papierkorb. Das nächtliche System-Backup
schreibt alles, Papierkorb eingeschlossen, aufs NAS.
- Vorteil: am wenigsten Code.
- Nachteil: kein Archiv im eigentlichen Sinn, keine Wiederverwendung, kein
  Projekt-Archivieren, Agenten können nichts ablegen.

## Empfehlung

**Option B**, in Etappen gebaut. Jede Etappe bringt für sich schon etwas:

1. **Speicher + Einstellungen:** Admin → Einstellungen → „Archiv & Sicherung“
   mit Ziel (lokaler Pfad oder NAS), Server, Freigabe, Unterordner und
   Zugangsdaten (aus dem Credential-Speicher), dazu ein Knopf „Verbindung
   testen“. Treiber `local` und `smb`, Katalog-Tabelle.
2. **Löschen archiviert:** Agent, Nutzer, Projekt und externe Instanz. Löschen
   nur nach erfolgreichem Schreiben, sonst Abbruch. Ehrliche Dialogtexte.
   Skript für die vorhandenen Waisen.
3. **Projekt archivieren:** Status `archived` macht endlich etwas. Das Projekt
   wird gepackt, ins Archiv gelegt und aus der Liste genommen. Wiederherstellen
   per Knopf.
4. **System-Backup aufs Archiv:** Knopf „Backup ins Archiv“ und ein Zeitplan
   (z. B. nächtlich). Der Download bleibt.
5. **Archiv-Ansicht + Agent-Werkzeuge:** Liste mit Filter, Wiederherstellen,
   `archive_put/list/get` für Agenten mit Rechteprüfung.
6. **Archiv als Wissen:** Textdateien archivierter Stücke ins Datamining, eigene
   Quelle „Archiv“.

Trade-off: Bis alles fertig ist, dauert es länger als bei A. Dafür muss nichts
umgebaut werden, wenn später ein anderes Ziel dazukommt. Aufrufer wie „Agent
löschen“ hängen nur an der Archiv-API, nicht am NAS.

## Entscheidung Till (13.10.): Löschen fragt immer nach

> Löschen blockieren und nachfragen, ob der Agent unwiderruflich gelöscht
> werden soll oder wohin er gespeichert werden soll.

> Wir legen eine System-Samba-Freigabe lokal für die Backups an. Wenn kein
> Server verfügbar ist, soll es lokal in dem Samba-Share hängen, der nicht an
> ein Projekt gebunden ist — ein System-Share, kein Agenten-Share. Darin
> werden die Backups gespeichert, damit ich sie per Samba herunterladen kann.

### Archiv-Speicher: zwei Stufen

1. **Externer Server** (NAS), falls in den Einstellungen eingetragen und
   erreichbar. Damit ist das Archiv nicht auf derselben Maschine.
2. **Lokales System-Archiv**, sonst. Immer vorhanden, ohne Einrichtung.
   - Ort: einstellbar (`HH_ARCHIVE_LOCAL_DIR`), Standard `$HH_DATA_DIR/archive/`.
     **Achtung Prod:** `$HH_DATA_DIR` liegt auf der kleinen Platte (`md127`,
     469 GB, 412 GB frei). Nur `workspaces/` ist per Bind-Mount auf die große
     Platte gelegt (`/var/lib/hydrahive2.hdd/workspaces` auf `sda2`, 14 TB
     frei). Für Prod daher `HH_ARCHIVE_LOCAL_DIR=/var/lib/hydrahive2.hdd/archive`
     setzen, sonst passen große Projekte nicht. Der Installer legt den Ordner
     an.
   - **Ein Ort für Dienst und Installer:** Der Dienst liest
     `/etc/hydrahive2/env`, `update.sh` und `install.sh` lesen `install.conf`.
     Darum steht `HH_ARCHIVE_LOCAL_DIR` in `install.conf`, und der Installer
     schreibt denselben Wert in die systemd-Unit des Dienstes
     (`Environment=`), so wie `HH_DATA_DIR`. Es gibt keine zweite Stelle, die
     auseinanderlaufen kann. Für Prod: Till trägt die Zeile einmal in
     `install.conf` ein und startet `update.sh`.
   - **Samba-Freigabe `HydraHive_Archiv`**, systemweit und an kein Projekt
     gebunden. **Lesen und schreiben** (Till, 13.10.): herunterladen und
     eigene Dateien hineinlegen. Zugang mit dem vorhandenen Samba-Nutzer `hh`
     (Passwort in `samba.password`), wie die Projekt-Freigaben.
     - `force user = hydrahive`, `force group = hydrahive`, Masken 0664/2775:
       Was übers Netz hineinkommt, gehört dem Dienst. HydraHive kann es lesen,
       katalogisieren und später als Wissen nutzen.
     - **Samba-Papierkorb** (`vfs objects = recycle`): Übers Netz Gelöschtes
       landet in `archive/.papierkorb/` statt sofort weg zu sein
       (`recycle:keeptree`, `recycle:versions`, `recycle:touch`). Leeren nur
       von Hand. So bleibt Tills Regel „keine Daten verlieren“ auch beim
       Schreibrecht erhalten.
     - Fremde Dateien ohne `.json` daneben zeigt die Archiv-Ansicht (Etappe 6)
       als „von Hand abgelegt“, ohne Wiederherstellen-Knopf.
   - Eigene Datei `/etc/samba/hh-projects.d/_system-archiv.conf`, die
     `_index.conf` mit einbindet. Der Projekt-Code (`enable_share`,
     `disable_share`) fasst sie nicht an.
   - Angelegt bei Installation und Update (`47-samba.sh`), wenn Samba an ist.
     Ohne Samba gibt es das Archiv trotzdem, nur eben ohne Netzfreigabe.

**Gibt es dann noch ein „nicht erreichbar“?** Nur für den externen Server.
Ist er eingetragen, aber weg, fragt der Dialog: „NAS nicht erreichbar: ins
lokale Archiv oder abbrechen?“. Er schreibt nicht still lokal. Das lokale
Archiv ist voll oder nicht beschreibbar → Löschen bricht ab.

### Lösch-Dialog (Agent, Projekt, Nutzer)

| Weg | Was passiert |
|---|---|
| **Ins Archiv** (vorausgewählt) | Packen (tar.gz + `archiv.json`), ins Ziel schreiben, Prüfsumme vergleichen, erst dann löschen. Der Dialog nennt das Ziel („NAS“ bzw. „lokales Archiv, Samba-Freigabe HydraHive_Archiv“). |
| **Unwiderruflich löschen** | wie heute, aber nur nach Eintippen des Namens |

- Der Dialog zeigt, was betroffen ist: Name, Größe, beim Projekt die Zahl der
  mitgelöschten Agenten und Sessions, sowie den freien Platz am Ziel. Passt
  es nicht, ist „Ins Archiv“ gesperrt und nennt den Grund.
- Großes Projekt (Prod: „HDD Archive“ 988 GB): Das Packen läuft im
  Hintergrund, mit Fortschritt im Dialog. Gelöscht wird erst nach
  erfolgreichem Packen. Eingehängte Laufwerke (`mounts/…`) kommen nie ins Paket.
- API: `DELETE` ohne `mode` ergibt `409 delete_mode_required` mit möglichen
  Zielen, Größe und freiem Platz. Ein Löschen ohne Wahl ist ausgeschlossen.
- Agenten haben heute kein Werkzeug zum Löschen von Agenten oder Projekten.
  Das bleibt so.

Ein Browser-Download ist damit nicht nötig. Die Archive liegen in der
Freigabe und lassen sich per Samba holen.

### Aufbau im Archiv

```
archive/
  agents/    2026-10-13_101500_<name>_<id>.tar.gz   + .json
  projects/  2026-10-13_101500_<name>_<id>.tar.gz   + .json
  users/     …
  backups/   (Etappe 4: System-Backups)
```

Neben jedem Paket liegt die `.json` mit Name, Art, Besitzer, Projekt,
Zeitpunkt, Grund, Größe und Prüfsumme. So ist es auch im Windows-Explorer
lesbar. Sie bildet zugleich den Katalog, aus dem die Archiv-Ansicht
(Etappe 5) liest.

## Etappen (angepasst)

1. **Archiv-Kern + lokales System-Archiv + Samba-Freigabe + Admin-Fenster:**
   Paket bauen (tar.gz, Prüfsumme, `.json`), ins lokale Archiv schreiben,
   Freigabe `HydraHive_Archiv` (lesen + schreiben, Papierkorb) bei Install und
   Update, `HH_ARCHIVE_LOCAL_DIR` über `install.conf` an Dienst und Installer.
   Admin-Fenster „Archiv & Sicherung“ mit Speicherort, Samba-Freigabe
   (inkl. Papierkorb leeren) und Liste der archivierten Elemente.
2. **Lösch-Dialog** für Agent, Projekt und Nutzer: Archiv oder unwiderruflich,
   API `mode` Pflicht, Packen im Hintergrund mit Fortschritt. Skript für die
   vorhandenen Waisen (Prod 30, hydratest 343).
3. **Externer Server** (NAS): Einstellungen, Zugangsdaten, Verbindungstest.
   Wenn eingetragen, ist er Ziel Nr. 1.
4. Projekt archivieren · 5. System-Backup ins Archiv · 6. Archiv-Ansicht +
   Agent-Werkzeuge · 7. Archiv als Wissen.

Nach 1 und 2 geht nichts mehr still verloren, auch ganz ohne NAS.

## Admin-Konsole (Till, 13.10.: „alles dazu muss auch in die Admin-Konsole“)

Ist-Stand, im Browser auf hydratest angesehen (13.10.):
- Admin-Seite `/admin` mit den Spalten „Admin-Bereiche“ (System, User, Module,
  Extensions, Plugins, Credentials), „Betriebszentrale“ und „Wartung & Backups“
  (Karten Backup → `/system`, System-Settings, Freigaben).
- Fenster **System** (`/admin?section=system`) mit Karten untereinander, u. a.
  „SMB-Shares (Samba)“ (Status, Login `hh`, Passwort mit Auge/Kopieren) und
  „System-Backup“ (Knöpfe „Backup herunterladen“, „Backup wiederherstellen“).
- System-Settings (`/system/settings`) zeigen die Einträge aus
  `settings/editable.py`, gruppiert.

**Neu: eigenes Admin-Fenster „Archiv & Sicherung“** (`/admin?section=archive`,
Pfad `/archive`). Erreichbar über eine Karte in „Wartung & Backups“ und einen
Eintrag „Archiv“ in „Admin-Bereiche“. Inhalt je Etappe:

| Bereich im Fenster | Etappe | Inhalt |
|---|---|---|
| **Speicherort** | 1 | Aktives Ziel (lokal / NAS), Pfad, freier und belegter Platz, Zahl der Pakete. Erreichbarkeit grün/rot. |
| **Samba-Freigabe** | 1 | Name `HydraHive_Archiv`, Adresse zum Kopieren (`\\<host>\HydraHive_Archiv`), Login `hh`, Passwort (Auge/Kopieren wie in der Samba-Karte), Papierkorb-Größe, Knopf „Papierkorb leeren“ (mit Namens-Bestätigung „Papierkorb“). Ist Samba aus: Hinweis + Knopf „Samba einrichten“ (vorhandener Zusatz-Modul-Weg). |
| **Archivierte Elemente** | 1 (Liste), 6 (Wiederherstellen) | Tabelle: Art, Name, Herkunft, Besitzer, Datum, Grund, Größe. Filter nach Art. In Etappe 1 nur lesen; „von Hand abgelegt“ markiert. |
| **Laufende Vorgänge** | 2 | Packen im Hintergrund mit Fortschritt (z. B. großes Projekt), Fehler sichtbar. |
| **Waisen** | 2 | Anzahl verwaister Arbeitsordner, Knopf „Ins Archiv verschieben“ (statt Skript; Skript bleibt als Rückfall für Prod ohne Oberfläche). |
| **Externer Server (NAS)** | 3 | Server, Freigabe, Unterordner, Zugangsdaten (Auswahl aus Credentials, Typ `basic`), Knopf „Verbindung testen“, Schalter „aktiv“. |
| **System-Backup ins Archiv** | 5 | Knopf „Jetzt sichern“, Zeitplan, letzte Sicherung. Die Karte „System-Backup“ im System-Fenster verweist hierher. |

Einstellungen (Pfad `HH_ARCHIVE_LOCAL_DIR`) stehen **nur lesend** im
Fenster, weil sie über `install.conf` an Installer und Dienst gehen
(s. o.). Änderbar über `update.sh`. Ein Knopf, der nur die Dienst-Seite
änderte, würde die beiden auseinanderlaufen lassen.

Alle Aktionen nur für Admins (`require_admin`). Texte de/en.

## Entschieden (Till, 13.10.)

- Löschen fragt immer: Archiv oder unwiderruflich (Name eintippen).
- Lokales System-Archiv mit eigener Samba-Freigabe, falls kein externer
  Server da ist. Die Freigabe ist **lesbar und beschreibbar**, mit
  Papierkorb als Sicherheitsnetz.
- Reihenfolge: zuerst lokales Archiv und Lösch-Dialog, dann der externe Server.
- Alles dazu kommt auch in die Admin-Konsole: eigenes Fenster „Archiv & Sicherung“.

**Status: Etappe 1 freigegeben (Till, 13.10.).**

## Etappe 1: Bauplan

### Backend `core/src/hydrahive/archive/`

| Datei | Inhalt |
|---|---|
| `_paths.py` | `archive_root()` aus `settings.archive_local_dir`; Unterordner `agents/ projects/ users/ backups/ uploads/`; `.papierkorb/` |
| `package.py` | `pack(kind, name, source_id, owner, reason, sources: list[(arcname, Path)], extra: dict) -> Entry`. Schreibt `…tar.gz.part`, berechnet sha256 beim Schreiben, `os.replace` auf den Endnamen, danach `.json`. Ohne eingehängte Laufwerke (`os.path.ismount`) und ohne `is_excluded`. Symlinks werden als Symlinks gesichert und nicht verfolgt. |
| `catalog.py` | `list_entries(kind=None)`: liest alle `.json` und listet Dateien ohne `.json` als `manual`. `usage()`: Platz frei/belegt, Anzahl, Papierkorb-Größe. Nichts davon in der DB, der Katalog sind die `.json`-Dateien (so bleibt er auch beim Bearbeiten über Samba stimmig). |
| `trash.py` | `empty_trash()`: löscht nur innerhalb von `archive_root()/.papierkorb`, ohne Symlinks zu folgen |

Name des Pakets: `JJJJ-MM-TT_HHMMSS_<name-sicher>_<id8>.tar.gz`. Der Name wird auf
`[A-Za-z0-9_-]` gekürzt (max. 40). Sicherheit: `kind` aus fester Liste, Ziel
immer unter `archive_root()` (resolve + Präfix-Prüfung).

Etappe 1 baut `pack()`. Aufrufer kommen erst in Etappe 2 (Löschen). Getestet
wird es direkt.

### Settings
`_ArchiveMixin.archive_local_dir`: `HH_ARCHIVE_LOCAL_DIR`, sonst
`data_dir/"archive"`. `archive_share_name`: `HydraHive_Archiv`.

### API `GET/POST /api/admin/archive/…` (nur Admin)
- `GET /status`: Ziel `local`, Pfad, existiert, beschreibbar, Platz,
  Anzahl je Art, Papierkorb-Größe; Samba: installiert, Freigabe aktiv,
  Freigabe-Name, Login, Passwort (wie `/api/system/samba/status`).
- `GET /entries?kind=`: Liste aus `catalog.list_entries`.
- `POST /trash/empty` mit `{"confirm": "Papierkorb"}`; sonst 400.

### Installer
- `install.sh`: `HH_ARCHIVE_LOCAL_DIR` in `CONF_VARS` (wird gespeichert, falls gesetzt).
- `50-systemd.sh`: `Environment=HH_ARCHIVE_LOCAL_DIR=…` in die Unit, falls gesetzt.
  `update.sh` erkennt eine Abweichung zur Unit und schreibt sie neu.
- `lib/archive-share.sh` (`hh_archive_ensure`): legt den Archiv-Ordner an
  (`hydrahive:hydrahive`, 2775) und schreibt `_system-archiv.conf` in
  `hh-projects.d`. Aufgerufen aus `47-samba.sh` und `update.sh`, wenn
  Samba an ist. Ohne Samba wird nur der Ordner angelegt.
- `_index.conf` erzeugt der Kern (`samba/manager._regenerate_index`). Er nimmt
  schon heute jede `*.conf` außer `_index.conf` auf, also auch
  `_system-archiv.conf`. Der Installer schreibt den Index nach dem Anlegen einmal neu.

Freigabe-Block:
```
[HydraHive_Archiv]
   comment = HydraHive System-Archiv
   path = <archive_local_dir>
   browseable = yes
   read only = no
   valid users = <samba_user>
   force user = <hh_user>
   force group = <hh_user>
   create mask = 0664
   directory mask = 2775
   vfs objects = recycle
   recycle:repository = .papierkorb
   recycle:keeptree = yes
   recycle:versions = yes
   recycle:touch = yes
   recycle:exclude_dir = .papierkorb
```

### Frontend
- `features/archive/`: `api.ts`, `ArchiveOverlay.tsx` (drei Bereiche:
  Speicherort, Samba-Freigabe, Elemente), Teil-Komponenten < 200 Zeilen, i18n de/en.
- Admin-Registry: `archive` (Pfad `/archive`), Karte in „Wartung & Backups“,
  Eintrag „Archiv“ in „Admin-Bereiche“.

### Tests (zuerst rot)
- `pack`: Inhalt, Prüfsumme, `.json`, kein Mount im Paket, Symlink bleibt
  Symlink, abgebrochenes Packen hinterlässt kein Paket, Name sicher.
- Katalog: `.json`-Einträge, fremde Dateien als `manual`, `.papierkorb` nicht gelistet.
- Papierkorb leeren: nur innerhalb, Symlink nach draußen wird nicht verfolgt.
- API: nur Admin, Bestätigungswort Pflicht.
- Installer: Freigabe-Block, Index enthält die Datei, `CONF_VARS`, Unit-Zeile.
- vitest: Fenster zeigt drei Bereiche, Samba aus → Hinweis + Knopf.
- E2E hydratest: Freigabe per `smbclient` lesen + schreiben, Löschen über
  Samba landet im Papierkorb, Fenster im Browser.
