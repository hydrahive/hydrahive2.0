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
   - **Ort ohne Einrichtung, auf jedem Server sinnvoll** (Till, 13.10.: „es MUSS
     ALLES über die Admin-Konsole gehen“, es gibt viele Installationen, die wir
     nicht kennen): Standard ist `workspaces/archive/`, also dieselbe Platte wie
     die Projektdaten. Wer `workspaces/` auf eine große Platte gelegt hat (Prod:
     16-TB-Platte per Bind-Mount, `$HH_DATA_DIR` selbst nur 469 GB), hat das
     Archiv automatisch dort. Kein Eintrag in `install.conf`, keine Unit-Zeile,
     kein Schritt im Installer.
   - Der gewählte Ort steht in `config_dir/archive.json` (`{"local_dir": …}`).
     Geschrieben wird er nur über die Admin-Konsole (Etappe 1b: Ort wechseln).
     Fehlt die Datei, gilt der Standard. Eine Env-Variable gibt es nicht.
   - **HydraHive legt Ordner und Freigabe selbst an** (`archive/setup.py`,
     beim Start und bei jedem Status-Aufruf, idempotent, ohne root):
     Ordner mit festen Unterordnern (2775), Freigabe-Datei
     `_system-archiv.conf` in `hh-projects.d`, `_index.conf` über den
     vorhandenen `samba/manager._regenerate_index`. Gemessen auf hydratest:
     smbd übernimmt neue Freigaben aus `hh-projects.d` für neue Verbindungen
     sofort, ein Reload (braucht root) ist nicht nötig.
   - **Nicht ins System-Backup und nicht in den Restore:** Das Archiv liegt
     unter `workspaces/`, das komplett gesichert wird. Ohne Ausnahme würde
     jedes Backup das ganze Archiv enthalten (Backup im Backup) und ein
     Restore das Archiv durch den alten Stand ersetzen. `backup/_paths` nimmt
     genau den Ordner `workspaces/archive` aus (nicht jeden Ordner namens
     „archive“), der Restore lässt ihn stehen.
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
   - Ein Schalter in der Admin-Konsole schaltet die Freigabe aus und wieder
     ein (`config_dir/archive.json`: `"share": false`). Standard: an, sobald
     Samba eingerichtet ist. Ohne Samba gibt es das Archiv trotzdem, nur eben
     ohne Netzfreigabe; das Fenster bietet dann „Samba einrichten“ an.

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
   Paket bauen (tar.gz, Prüfsumme, `.json`), ins lokale Archiv schreiben
   (Standard `workspaces/archive`), Freigabe `HydraHive_Archiv` (lesen +
   schreiben, Papierkorb) legt HydraHive selbst an, Schalter in der Konsole.
   Kein Installer-Teil.
1b. **Ort wechseln aus der Admin-Konsole:** Auswahl der Platten (mit freiem
   Platz), vorhandene Pakete im Hintergrund mit Fortschritt verschieben
   (Till, 13.10.: ja). Kann HydraHive auf der gewählten Platte nicht schreiben,
   richtet ein Knopf die Rechte ein (über den vorhandenen Root-Runner der
   Zusatz-Module, feste Aktion, Pfad geprüft; Till, 13.10.: ja).
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

**Regel (Till, 13.10.):** Alles, was ein Nutzer einstellen muss, geht über
dieses Fenster. Keine Shell, kein Terminal, keine Config-Datei von Hand,
auch nicht „einmalig vor dem Update“. Der Ort wird in Etappe 1 angezeigt
(mit Platte und freiem Platz) und ist ab Etappe 1b dort änderbar.

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

### Ort und Einrichtung (kein Installer-Teil)
- `archive/location.py`: `archive_root()` = `local_dir` aus
  `config_dir/archive.json`, sonst `settings.workspaces_dir / "archive"`.
  Kaputte Datei → Standard + Warnung im Log. `share_wanted()` aus derselben
  Datei, Standard an.
- `archive/setup.py` `ensure_archive()`: Ordner + Unterordner anlegen, und
  wenn `hh-projects.d` existiert und die Freigabe gewünscht ist:
  `_system-archiv.conf` schreiben (nur bei Änderung) und `_index.conf` über
  `samba.manager._regenerate_index()` neu schreiben. Ist die Freigabe nicht
  gewünscht: Datei entfernen, Index neu. Fehler werden gemeldet, nie
  geworfen (Start darf nicht scheitern). Aufruf: `lifespan` (im Thread) und
  `GET /status`.
- `PUT /api/admin/archive/share {"enabled": bool}`: Schalter.
- Backup: `backup/_paths.is_excluded` nimmt `workspaces/archive` aus (genau
  dieser Pfad). Restore: `_atomic_replace_dir` für `workspaces` lässt den
  vorhandenen `archive`-Ordner stehen.

### API `GET/POST /api/admin/archive/…` (nur Admin)
- `GET /status`: Ziel `local`, Pfad, existiert, beschreibbar, Platz,
  Anzahl je Art, Papierkorb-Größe; Samba: installiert, Freigabe aktiv,
  Freigabe-Name, Login, Passwort (wie `/api/system/samba/status`).
- `GET /entries?kind=`: Liste aus `catalog.list_entries`.
- `POST /trash/empty` mit `{"confirm": "Papierkorb"}`; sonst 400.

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
- Einrichtung: Standardort unter `workspaces`, `archive.json` gewinnt, kaputte
  Datei → Standard; Ordner + Freigabe-Datei + Index ohne root; Schalter aus →
  Datei weg; ohne Samba nur Ordner; Index bleibt für das Backend schreibbar.
- Backup/Restore: `workspaces/archive` nicht im Backup, Restore lässt es stehen,
  andere Ordner namens `archive` (z. B. in Projekten) bleiben im Backup.
- vitest: Fenster zeigt drei Bereiche, Samba aus → Hinweis + Knopf, Schalter,
  Platte und freier Platz, kein Text mit `update.sh` oder `install.conf`.
- E2E hydratest: Freigabe per `smbclient` lesen + schreiben, Löschen über
  Samba landet im Papierkorb, Fenster im Browser.

## Etappe 1b: Ort wechseln aus der Admin-Konsole (Till, 13.10.: Umzug ja, Rechte-Knopf ja)

Ziel: Ein Admin, den wir nicht kennen, legt das Archiv ohne Terminal auf eine
andere Platte. Kein freies Pfadfeld: Er wählt eine Platte aus einer Liste.

### Auswahl
- `GET /api/admin/archive/locations`: Eintrag „Standard (bei den Projektdaten)“
  plus je **Platte** ein Eintrag. Platte = echtes lokales Dateisystem aus
  `/proc/self/mountinfo` (ext2/3/4, xfs, btrfs, zfs, f2fs, bcachefs), schreibbar
  eingehängt, je Gerät (MAJ:MIN) einmal: „/“ zuerst, dann ein Einhängepunkt mit
  echter Wurzel, dann der kürzeste. Bind-Mounts zählen mit, weil in Containern
  (incus, LXC, Docker) schon „/“ einer ist (Fund auf hydratest, 13.10.). Nicht angeboten:
  Netzlaufwerke (kommen mit Etappe 3), `/boot*`, `/home` (Dienst sieht es nur
  lesend), `/tmp`, alles unter `workspaces/` (Projekt-Mounts).
- Ziel auf der Platte ist immer der Ordner `hydrahive-archiv` direkt im
  Einhängepunkt; für `/` ist es `/srv/hydrahive-archiv`.
- Je Eintrag: Größe, frei, ob HydraHive dort schreiben darf, ob es der aktuelle
  Ort ist.

### Rechte-Knopf
- Darf HydraHive auf der gewählten Platte nicht schreiben: Knopf „Platte für
  HydraHive einrichten“. Er nutzt den vorhandenen Root-Runner der Zusatz-Module
  (`installer/addon-ctl.sh`, Anfrage `prepare-archive <einhängepunkt>`).
- Der Runner prüft selbst noch einmal: echter Einhängepunkt, erlaubtes
  Dateisystem, kein gesperrter Ort, Ziel ist kein Symlink. Dann
  `mkdir`, `chown hydrahive:hydrahive`, `chmod 2775` – nur am Zielordner.

### Umzug im Hintergrund
- `POST /api/admin/archive/move {"location": "<id aus der Liste>"}` → 202.
  Vorher geprüft: Ziel schreibbar, leer (oder nur leere Unterordner), genug
  Platz (belegt + 5 % Reserve), nicht innerhalb des alten Orts und umgekehrt.
- Ablauf: Freigabe aus (niemand schreibt mehr hinein) → Dateien kopieren mit
  Fortschritt (Bytes, Dateien) → prüfen (Pakete per sha256 aus der `.json`,
  übrige per Größe) → Ort in `archive.json` umstellen, Freigabe am neuen Ort
  an → **nur die geprüft kopierten** Dateien am alten Ort löschen. Was dort
  sonst noch liegt, bleibt liegen und wird gemeldet.
- Fehler vor dem Umstellen: Kopie am Ziel wird entfernt, alter Ort bleibt
  unverändert aktiv, Freigabe wieder an. Neustart mitten im Umzug: Zustand
  steht in `config_dir/archive-move.json`, beim Start wird ein halber Umzug
  genauso zurückgerollt (vor dem Umstellen) bzw. das Aufräumen fortgesetzt
  (nach dem Umstellen).
- Während des Umzugs lehnt `pack()` ab (Etappe 2 zeigt das im Lösch-Dialog).
- Fortschritt steht in `GET /status` unter `move`; das Fenster fragt ihn ab.

## Etappe 2: Bauplan (Lösch-Dialog + Waisen)

Freigabe Till (13.10.): (1) Projekt = ein Paket (Arbeitsordner, Konfig, alle
Agenten mit Gedächtnis, ohne eingehängte Laufwerke). (2) Beim Löschen eines
Nutzers kommen seine Projekte mit ins Archiv und werden mitgelöscht. (3) Leere
Waisen werden einfach entfernt, Waisen mit Inhalt archiviert. (4) Internes
Aufräumen (z. B. Storyteller `drop_project`) löscht weiter direkt.

### Ist-Stand (13.10., Code `8863541b`, Prod nur lesend)

- Fünf Stellen in der Oberfläche löschen mit `confirm()` direkt:
  `AgentFormTabs`, `ProjectDetailsOverlay` (Cockpit), `projects/_SettingsTab`,
  `UsersOverlay`, `_DataminingInstancesSection`. Die vier Routen sind nur für
  Admins. Module und Plugins rufen sie nicht über HTTP auf.
- `pack()` aus Etappe 1 hat noch keinen Aufrufer. Packstufe ist der
  tarfile-Standard 9. Gemessen an 400 MB gemischten Dateien: Stufe 9 braucht
  60 s (151 MB), Stufe 6 11 s (152 MB), Stufe 1 5 s (169 MB).
- Größtes Projekt auf Prod: „HDD Archive“, 1,06 TB in 1,85 Mio. Dateien.
  Allein das Zählen der Größe dauert 68 s.
- Chats liegen in `sessions.db` und bleiben dort heute auch nach dem Löschen
  eines Agenten. Auf Prod: 113 Sessions mit 8.605 Nachrichten von 41
  gelöschten Agenten.
- Waisen auf Prod: 30 Arbeitsordner ohne Agent (28 leer, `05b3454f…` 144 KB
  Recherche, `2efc2a67…` 278 MB `rom`). Dazu **7 Agenten ohne Projekt**:
  Storyteller-Helfer vom 07.10. (vor #527), je 3 KB, ohne Sessions.
  hydratest: 2 leere Arbeitsordner.
- Geheimnisse: Agent-Konfigs enthalten keine. Projekt-Konfigs enthalten
  `webhook_secret` (18) und `git_token` (6) im Klartext. Die Zugangsdaten
  eines Nutzers (`credentials/<name>.json`) sind verschlüsselt. In den
  `.git/config` der Arbeitsordner stehen keine Zugangsdaten (29 geprüft).

**Gefundene Fehler (werden in Etappe 2 mit behoben):**

1. **Projekt löschen kann Daten auf dem NAS löschen.** `projects/config.delete()`
   ignoriert, ob das Aushängen eines Netzlaufwerks geklappt hat, und ruft dann
   `shutil.rmtree` auf. `rmtree` beachtet keine Laufwerksgrenzen. Scheitert das
   Aushängen (Zeitüberschreitung, „busy“), löscht es Dateien auf dem
   Fileserver mit.
2. **Nutzer löschen lässt Daten unter seinem Namen liegen.** Gelöscht werden
   nur seine Agenten, API-Schlüssel und Freigaben. Liegen bleiben: Projekte,
   die er angelegt hat (`created_by`), seine Mitgliedschaften in fremden
   Projekten, `credentials/<name>.json`, Butler-Abläufe, Zeitpläne, Skills,
   Notizen (Scratchpad) sowie WhatsApp- und Discord-Einstellungen. Alles davon
   hängt am **Namen**. Ein neuer Nutzer mit demselben Namen erbt es, auch die
   Admin-Rolle in den Projekten des alten Nutzers. Vermutung, wird zuerst mit
   einem Test belegt: Ein Butler-Zeitplan läuft nach dem Löschen weiter und
   legt dem gelöschten Nutzer einen neuen Buddy an.
3. Das Backend erlaubt, das eigene Konto und den letzten Admin zu löschen.
   Das verhindert heute nur die Oberfläche.

### Ablauf eines Löschvorgangs (Hintergrund-Auftrag)

Beide Wege laufen als Auftrag im Hintergrund, auch „unwiderruflich“: Ein
großes Projekt zu löschen dauert sonst länger als eine HTTP-Anfrage.

| Schritt | Ins Archiv | Unwiderruflich |
|---|---|---|
| 1. Sperren | Agenten auf `disabled` setzen (alter Status wird gemerkt), laufende Läufe abbrechen, Projekt-Freigabe aus | ebenso |
| 2. Messen | Größe ohne eingehängte Laufwerke, mit Fortschritt | – |
| 3. Platz prüfen | frei ≥ Größe + 5 %, sonst Abbruch mit Grund | – |
| 4. Packen | `pack()` mit Fortschritt (Bytes, Dateien), Stufe aus `settings.archive_compress_level` (Standard 1, s. o.) | – |
| 5. Prüfen | Paket ganz neu lesen: sha256 gleich `.json`, gzip fehlerfrei, Zahl der Einträge stimmt | – |
| 6. Löschen | Laufwerke aushängen. Scheitert das: Abbruch vor dem ersten Löschen. Dann löschen, ohne je in ein eingehängtes Laufwerk zu gehen (Fehler 1) | ebenso |

- Fehler in Schritt 1–5: Es wird nichts gelöscht. Halbes Paket weg, Agenten
  wieder auf den alten Status, Freigabe wieder an. Der Grund steht im Auftrag.
- Fehler in Schritt 6: Das Paket bleibt (die Daten sind sicher). Der Auftrag
  meldet, was noch übrig ist. Ein neues Löschen räumt den Rest weg.
- Neustart mitten im Auftrag: Zustand steht in `config_dir/archive-jobs.json`.
  Vor Schritt 6 wird zurückgerollt wie bei einem Fehler, ab Schritt 6 wird das
  Löschen fortgesetzt.
- Es läuft immer nur ein Auftrag. Weitere warten in einer Reihe. Ein Objekt,
  das schon im Auftrag ist, lässt sich nicht noch einmal löschen
  (`409 delete_in_progress`).
- Zieht das Archiv gerade um (Etappe 1b), ist „Ins Archiv“ gesperrt
  (`archive_unavailable`, Grund `moving`). „Unwiderruflich“ geht weiter.
- Arbeitsdateien (Sessions als JSON) entstehen in `archive/.arbeit/<auftrag>/`.
  Sie liegen auf derselben Platte wie das Archiv, der Katalog zeigt sie nicht
  und sie werden danach entfernt.

### Was in welches Paket kommt

| Art | Inhalt |
|---|---|
| **Agent** | `agents/<id>` vollständig (Konfig, Prompt, Gedächtnis, Kristalle, Soul, …), eigener Arbeitsordner (`master/` bzw. `specialists/`, nicht der Projekt-Ordner), seine Chats als `sessions/<id>.json` (Nachrichten + Werkzeugaufrufe, eine Datei je Chat) |
| **Projekt** | `projects/<id>`, Arbeitsordner ohne eingehängte Laufwerke, alle Agenten des Projekts wie oben, Chats des Projekts. In der `.json`: übersprungene Laufwerke, Mitglieder |
| **Nutzer** | Nutzer-Eintrag ohne Passwort-Hash, seine Agenten (ohne Projekt-Agenten), `credentials/<name>.json` (bleibt verschlüsselt), Skills, Butler-Abläufe, Zeitpläne, WhatsApp/Discord-Einstellungen (Bot-Token als `***`), Morgen-Briefing (`zahnfee/<name>.json`). **Je eigenes Projekt ein eigenes Projekt-Paket**, verknüpft über `extra.part_of`, damit sich ein Projekt später auch ohne den Nutzer wiederverwenden lässt |
| **Externe Instanz** | wie Agent, dazu der Nutzer-Eintrag der Instanz. API-Schlüssel kommen nicht mit, sie werden ungültig |

Geheimnisse im Paket: siehe Frage 2.

Ob die Chats danach aus `sessions.db` entfernt werden, klärt Frage 1. Der
Dialog sagt in jedem Fall, wo sie noch liegen.

### Nutzer löschen: zusätzlich (Fehler 2 + 3)

- Abgelehnt mit `400 cannot_delete_self` bzw. `400 last_admin_cannot_delete`.
- Nach dem Packen (bzw. sofort bei „unwiderruflich“) wird alles entfernt, was
  am Namen hängt: Projekte mit `created_by` = Nutzer, seine Mitgliedschaften
  in fremden Projekten, Zugangsdaten (samt SSH-Schlüssel-Dateien), Skills,
  Butler-Abläufe, Zeitpläne, WhatsApp/Discord (laufende Verbindung wird
  getrennt, das WhatsApp-Login `whatsapp/<name>/auth` gelöscht, sonst wäre ein
  Namensvetter mit dem alten Konto verbunden), Morgen-Briefing.
- Ebenso die persönlichen Zeilen in Kern-Tabellen, die am Namen oder an der
  `user_id` hängen: `user_preferences`, `prompt_archive`,
  `streaming_credentials`, `streaming_jobs`, `teamchat_identities`,
  `vault_pins`, `health_ingest`, `health_daily`, `fhir_resources`,
  `ega_records` (Fund beim Bau, 13.10.). Sie kommen als `db/<tabelle>.jsonl`
  ins Nutzer-Paket. Verschlüsselte Spalten bleiben verschlüsselt.
  Protokolle (`llm_calls`, `errors_log`, Audit-Tabellen) bleiben stehen.
- Agenten des Nutzers in fremden Projekten gehören zum Projekt. Sie bleiben
  und gehen an den Ersteller des Projekts über.
- Bleibt bestehen und steht so im Dialog: VMs, Container und SMB-Verbindungen
  des Nutzers sowie Daten in Modulen (Notizbuch, Cryptoboard, Haushaltsbuch,
  Aufgaben …, rund 30 Tabellen). Siehe Entscheidung 3.

### API

- `GET /api/admin/archive/delete-preview?kind=agent|project|user|instance&id=…`:
  Name, was betroffen ist (Agenten, Chats, Projekte mit Mitgliedern, was
  bestehen bleibt, übersprungene Laufwerke), Größe, Ziel (Pfad, Freigabe,
  freier Platz) und ob „Ins Archiv“ geht (sonst Grund). Die Größe wird höchstens
  `settings.archive_preview_budget_s` (Standard 5 s) gezählt. Dauert es
  länger, kommt „mindestens X“ zurück, und Schritt 3 prüft später die genaue
  Größe.
- Die vorhandenen Routen `DELETE /api/agents/{id}`, `/api/projects/{id}`,
  `/api/users/{name}` und `/api/external-instances/{id}` bekommen
  `?mode=archive|permanent&confirm=<name>`:
  - ohne `mode`: `409 delete_mode_required`
  - `permanent` und `confirm` ist nicht genau der Name: `400 delete_confirm_mismatch`
  - sonst `202 {"job_id": …}`, statt bisher 204
- `GET /api/admin/archive/jobs`: laufender Auftrag, wartende, die letzten 20
  fertigen (Schritt, Bytes, Dateien, Fehler). Steht auch in `GET /status`.
- Python-Funktionen wie `agent_config.delete()` und `project_config.delete()`
  bleiben direkt, für internes Aufräumen (Entscheidung 4). Den Fix für Fehler 1
  bekommen sie trotzdem.

### Oberfläche

- `features/archive/delete/DeleteDialog.tsx`, genutzt von allen fünf Stellen.
  Er zeigt, was betroffen ist und was bestehen bleibt, und bietet zwei Wege an:
  - **Ins Archiv**: vorausgewählt, wenn es geht. Er nennt Ziel und freien
    Platz. Geht es nicht, ist der Weg gesperrt, und der Grund steht daneben.
  - **Unwiderruflich**: nie vorausgewählt, nur nach Eintippen des Namens.
- Nach dem Start: Fortschritt im Dialog. Schließen ist erlaubt, der Auftrag
  läuft weiter.
- Admin-Fenster „Archiv & Sicherung“, neuer Bereich **Laufende Vorgänge**:
  Lösch-Aufträge und Umzug mit Fortschritt und Fehlern.
- Texte de/en, ohne `update.sh` und ohne `install.conf` (Test wie in Etappe 1).

### Waisen (eigener PR)

- `GET /api/admin/archive/orphans`: Arbeitsordner ohne Agent (leer oder mit
  Inhalt, Größe) und Agenten, deren Projekt nicht mehr existiert.
- `POST /api/admin/archive/orphans/cleanup` → 202, als Auftrag in derselben
  Reihe. Leere Ordner entfernen. Ordner mit Inhalt und Agenten ohne Projekt
  ins Archiv (Art `agents`, Grund `orphan`), dann entfernen. Unmittelbar vor
  dem Entfernen wird noch einmal geprüft, ob es wirklich eine Waise ist.
- Bereich **Waisen** im Admin-Fenster: Anzahl, Größe, Knopf „Aufräumen“.
- Ein Skript gibt es nicht. Nach Tills Regel geht alles über die Admin-Konsole.

#### Bauplan 2b (14.10., Ist-Stand hydratest: 268 Spezialisten-Ordner ohne Agent, 1 davon mit Inhalt; 71 Buddy-Ordner ohne Agent)

- **Was ist eine Waise?**
  - Ein Ordner `workspaces/specialists/<id>` oder `workspaces/master/<id>`, zu dem es keinen Agenten gibt. Nur gültige Agent-IDs, keine Symlinks.
  - Ein Agent, dessen `project_id` auf ein Projekt zeigt, das es nicht mehr gibt.
  - Projekt-Ordner `workspaces/projects/<id>` sind nicht Teil von 2b.
- **„Leer“ heißt:** Es liegt nur drin, was HydraHive selbst anlegt. Das sind die unveränderte `startup.md` aus der Vorlage und im Buddy-Ordner unter `projects/` die Verknüpfungen auf Projektordner (`agents/_workspace_links.py`), auch solche, die ins Leere zeigen. Ein Link irgendwohin sonst zählt als Inhalt. Verknüpfungen werden nie betreten. Ob ein Ordner leer oder voll ist, hängt nie vom Zeitbudget ab. Nach Ablauf des Budgets wird nur die Größe nicht weitergezählt.
  - Gefunden auf hydratest: Zuerst galten nach Ablauf des Budgets alle weiteren Ordner als „mit Inhalt“. Danach galten 11 Buddy-Ordner nur wegen ihrer Projekt-Links als „mit Inhalt“.
- `GET /api/admin/archive/orphans` zählt höchstens `archive_preview_budget_s` lang und meldet danach „mindestens“.
- `POST /api/admin/archive/orphans/cleanup` mit `{"workspaces": [...], "agents": [...]}`: genau die IDs, die das Fenster angezeigt hat. Neue Waisen, die erst nach dem Anzeigen entstanden sind, bleiben unberührt.
  - Die Ordner laufen als **ein** Auftrag `orphans` in derselben Reihe. Der Auftrag merkt sich das Paket, bevor er schreibt. Ein Neustart verwirft nur das Paket, dessen Ordner noch nicht entfernt war.
  - Jeder Agent ohne Projekt wird ein eigener normaler Lösch-Auftrag (`agent`, `archive`, Grund `orphan`). So gelten Sperren, Chats, Maskierung, Prüfung und Neustart-Sicherheit wie in 2a. Hat der Agent bis dahin wieder ein Projekt, endet der Auftrag mit `not_orphan`, und es wird nichts gelöscht.
- Pakete: Art `agents`, Grund `orphan`, Name „Arbeitsordner <ID kurz>“.
- Im Fenster gibt es keine Rückfrage, denn nichts mit Inhalt geht verloren. Der Bereich zeigt die Anzahl leerer Ordner, die Anzahl mit Inhalt samt Größe und die Agenten ohne Projekt.

### Tests (zuerst rot)

- Routen: ohne `mode` → 409. Falscher Name → 400. Nur Admin. Eigenes Konto
  bzw. letzter Admin → 400.
- Agent/Projekt/Nutzer/Instanz ins Archiv: Paket enthält das Erwartete, Chats
  als JSON, kein Laufwerk. Gelöscht wird erst nach der Prüfung.
- Packen scheitert (Platte voll simuliert) und Prüfung scheitert (Paket
  verändert): Es wird nichts gelöscht, Agenten haben wieder den alten Status.
- Aushängen scheitert: Es wird nichts gelöscht, Dateien „im Laufwerk“ bleiben
  (Fehler 1, auch für `project_config.delete()`).
- Nutzer: Am Namen hängt danach nichts mehr. Ein neuer Nutzer mit demselben
  Namen sieht nichts vom alten (Fehler 2). Butler-Zeitplan legt keinen Buddy
  mehr an.
- Neustart vor und nach Schritt 6, Reihe, `delete_in_progress`, Archiv zieht um.
- Waisen: leer → weg, mit Inhalt → Paket, inzwischen wieder zugeordnet →
  bleibt.
- vitest: „Unwiderruflich“ nie vorausgewählt, Knopf erst nach dem Namen,
  gesperrter Archiv-Weg mit Grund, Fortschritt, keine verbotenen Texte.
- E2E hydratest mit echtem Zustand: Test-Agent, Test-Projekt mit Chat und
  Laufwerk, Test-Nutzer mit Projekt im Browser löschen. Danach die Pakete per
  `smbclient` holen und den Inhalt prüfen. Gegenprobe auf `main` ist rot.
  Frischer `images:ubuntu/26.04`-Container.

### PRs

1. **2a**: Lösch-Wege + Auftrag + Dialog + „Laufende Vorgänge“ + Fehler 1–3.
   Backend und Oberfläche zusammen, weil die Routen danach `mode` verlangen.
2. **2b**: Waisen.

### Entschieden (Till, 13.10.)

1. **Chats verschwinden.** Bei beiden Wegen werden die Chats des Gelöschten
   aus `sessions.db` entfernt, bei „Ins Archiv“ erst nach der Prüfung des
   Pakets. Das Datamining behält seine Kopie. Der Dialog sagt das.
2. **Geheimnisse ersetzen.** `webhook_secret` und `git_token` in Projekt-
   Konfigs stehen im Paket als `***`. Die Zugangsdaten des Nutzers bleiben
   verschlüsselt, wie sie sind.
3. **Vorerst bleiben** VMs, Container, SMB-Verbindungen und Modul-Daten
   eines gelöschten Nutzers bestehen. Der Dialog zeigt sie mit Anzahl. Eigener
   Task: Schnittstelle „Nutzer gelöscht“ für Module.

**Status: Etappe 2 freigegeben (Till, 13.10.).**

### Funde beim Bau (13./14.10.)

- **Notizen (Scratchpad) sind ein Modul** (`data_dir/scratchpad/<user_id>`),
  kein Kern-Teil. Sie fallen unter Entscheidung 3 und bleiben vorerst liegen.
- **Fast alle persönlichen Kern-Tabellen schlüsseln mit dem Namen**, nicht mit
  der ID (`user_preferences`, `prompt_archive`, Streaming, Teamchat, Health,
  FHIR, eGA). Nur `vault_pins` nutzt die ID. Gelöscht wird jeweils mit dem
  Schlüssel, den die Tabelle wirklich benutzt.
- **Zweite Absicherung gegen den Buddy-Wiedergänger:** Zeitpläne und Butler
  legen keinen Buddy mehr für einen Nutzer an, den es nicht gibt (falls ein
  Lauf genau während des Löschens startet).
- **Wartende Aufträge laufen nach einem Neustart weiter.** Sie sind bestätigt
  und haben noch nichts angefasst. Zurückgerollt wird nur ein Auftrag, der
  vor Schritt 6 unterbrochen wurde.
- **Harter Abbruch mitten im Packen** (Strom weg, Neustart, im frischen
  Container mit 800 MB nachgestellt): Das halbe Paket (`.part`) blieb liegen.
  Jetzt merkt sich der Auftrag jeden Paketnamen, bevor er schreibt. Beim
  Zurückrollen verschwinden fertige Teilpakete und halbe `.part`-Dateien.
- **Ein Laufwerk, das umount mit „ok“ quittiert, aber noch hängt, gilt als
  gescheitert.** Ein von Hand eingehängtes Laufwerk (HydraHive kennt es
  nicht) bleibt samt Elternordnern stehen und steht im Ergebnis unter
  „übrig“.
- **Internes Löschen (`agent_config.delete`) nimmt den eigenen Arbeitsordner
  jetzt mit.** So entstehen keine neuen Waisen. `project_config.delete` wirft
  `ProjectDeleteBlocked`, wenn ein Laufwerk nicht aushängt (Fehler 1). Für
  Storyteller ändert sich nichts: Seine Projekte haben keine Laufwerke.
- **Ein Instanz-Nutzer kommt nur mit**, wenn er die Rolle `user` hat und keine
  weiteren Agenten besitzt. Das ist dieselbe Regel wie bisher in
  `external_instances`.
- Einstellungen (Standard, über ENV änderbar): `archive_compress_level` 1,
  `archive_preview_budget_s` 5, `archive_space_reserve` 0,05,
  `archive_jobs_keep` 20.

## Etappe 3: Bauplan (Kopie auf einen externen Server)

**Entschieden (Till, 14.10.): Weg B** – wie bisher lokal packen und prüfen,
danach automatisch eine Kopie auf den externen Server. Die lokale Kopie
bleibt, **lässt sich aber löschen**, sobald die Kopie auf dem Server geprüft
ist. Das ersetzt „NAS ist Ziel Nr. 1, sonst Rückfrage“ aus der Planung vom
13.10.: Löschen hängt nie am NAS, es gibt keine Rückfrage, wenn es weg ist.

### Ist-Stand (14.10.)

- **Prod-NAS**: `//192.168.178.3/Hydrahive_backups`, Unterordner `/hydrahive`,
  31 TB, 29 TB frei. Heute nur als Projekt-Laufwerk im DEV-Projekt
  eingehängt. Zugangsdaten `nasbackup_hydra` (Typ basic) gehören dem Nutzer
  `till`, nicht dem System.
- **Einhängen** (`smbmounts/mounter.py`) braucht root (`sudo -n bash
  mount.cifs`) und `cifs-utils`. Auf hydratest fehlen `mount.cifs` und
  `smbclient`, der Container ist privilegiert. Auf unbekannten
  Installationen ist beides nicht sicher vorhanden.
- **Gemessen**: Die Python-Bibliothek `smbprotocol` (MIT, braucht nur
  `cryptography` und `pyspnego`) spricht SMB2/3 direkt, ohne Einhängen,
  ohne root, ohne Systempakete. Gegen die Archiv-Freigabe auf hydratest:
  50 MB hoch mit 189 MB/s, zurücklesen mit 354 MB/s, Prüfsumme stimmt,
  `rename` von `.part` auf den Endnamen klappt.

### Wie die Kopie aufs NAS kommt: ohne Einhängen

- Neue Abhängigkeit `smbprotocol` im Kern (`core/pyproject.toml`). Der
  Installer und `update.sh` installieren sie über pip mit, ganz ohne
  Systempaket und ohne root. Das passt zu Tills Regel „alles automatisch
  bei Updates“.
- Kein `mount.cifs`, kein `sudo`, kein Laufwerk im Dateisystem. Damit kann
  auch nichts „in ein Laufwerk hinein löschen“ (Fehler 1 aus Etappe 2).
- Hochladen: `<paket>.part` schreiben, dabei sha256 mitrechnen, dann
  umbenennen in den Endnamen, danach die `.json`. Zum Prüfen das Paket vom
  Server **zurücklesen** und die sha256 vergleichen. Erst dann gilt die
  Kopie als „auf dem Server“.
- Ablage auf dem Server wie lokal: `<unterordner>/{agents,projects,users,
  backups,uploads}/<datei>.tar.gz` + `.json`. Damit ist das NAS auch ohne
  HydraHive lesbar.

### Einstellungen (Admin-Konsole, Bereich „Externer Server“)

- Server (Hostname oder IP), Freigabe, Unterordner (optional), Benutzer,
  Passwort, Schalter „aktiv“. Prüfung wie bei `smbmounts/models.py`
  (`HOST_RE`, `SHARE_RE`, `SUBPATH_RE`, kein `..`).
- **Die Zugangsdaten gehören dem System**, nicht einem Nutzer: Sie stehen
  in `config_dir/archive-remote.json`, das Passwort darin mit
  `credentials/_crypto.encrypt` verschlüsselt (derselbe Schlüssel wie bei
  den Nutzer-Zugangsdaten). Die API gibt das Passwort nie zurück, nur ob
  eines gesetzt ist. Ein leeres Passwortfeld beim Speichern behält das alte.
- **Knopf „Verbindung testen“**: anmelden, Unterordner anlegen falls nötig,
  eine kleine Probedatei schreiben, zurücklesen, löschen. Ergebnis mit
  Grund: Server nicht erreichbar, Anmeldung falsch, Freigabe unbekannt,
  keine Schreibrechte, oder ok mit freiem Platz.
- Gespeichert wird auch ohne erfolgreichen Test. Aktiv schalten geht erst
  nach einem erfolgreichen Test mit genau diesen Daten.

### Kopieren (Hintergrund, eigene Reihe)

- Nach jedem neuen Paket (Löschen, Waisen, später Backups) kommt ein
  Eintrag in die **Kopier-Reihe** (`config_dir/archive-remote-queue.json`).
  Ein eigener Thread arbeitet sie ab, unabhängig von der Lösch-Reihe:
  Ein langsames oder fehlendes NAS hält kein Löschen auf.
- **NAS nicht erreichbar**: Der Eintrag bleibt in der Reihe, neuer Versuch
  mit wachsendem Abstand (1 min, 5 min, 30 min, dann stündlich). Keine
  Rückfrage, kein Popup. Im Fenster steht, wie viele Pakete warten und
  warum.
- **Abgleich** (beim Start, nach „aktiv“ einschalten und auf Knopfdruck):
  Alle lokalen Pakete, die auf dem Server fehlen oder anders sind, kommen
  in die Reihe. So landen auch die Pakete aus Etappe 1 und 2 und von Hand
  abgelegte Dateien auf dem NAS.
- Stand je Paket in der lokalen `.json` (`remote: {state, sha256,
  verified_at}`) und in der Liste der Elemente: „nur lokal“, „lokal +
  Server“, „nur Server“, „wartet auf Kopie“.
- Neustart mitten im Hochladen: Die `.part` auf dem Server wird beim
  nächsten Versuch überschrieben, nichts gilt als kopiert, was nicht
  zurückgelesen und geprüft ist.

### Lokale Kopie löschen (Till, 14.10.)

- Pro Paket in der Liste und gesammelt („Alle lokalen Kopien löschen, die
  geprüft auf dem Server liegen“): Knopf **„Lokale Kopie löschen“**.
- Nur möglich, wenn die Kopie auf dem Server **unmittelbar vorher** noch
  einmal geprüft wurde: Sie existiert, und Größe und sha256 aus der
  Server-`.json` stimmen. Das sha256 aus der Server-`.json` muss dem der
  lokalen `.json` entsprechen. Ist der Server gerade nicht erreichbar, geht
  der Knopf nicht (Grund steht dabei).
- Bestätigung im Dialog ohne Namen-Eintippen, denn es geht nichts
  verloren. Der Text sagt, wo die Kopie liegt.
- Danach bleibt lokal nur die `.json` mit `remote.state = "remote_only"`
  stehen. Die Liste zeigt das Paket weiter („nur Server“), der Katalog
  bleibt vollständig. Platz wird frei.
- Später (Etappe 6, Wiederherstellen) holt HydraHive ein solches Paket
  vom Server zurück.
- **Kein automatisches Löschen der lokalen Kopie** in Etappe 3. Eine
  Einstellung „lokale Kopien nach X Tagen löschen“ kann später kommen.

#### Bauplan 3b (14.10., nach 3a auf Prod: 9 Pakete „verified“ auf dem NAS)

- Nur für **Pakete** (`.tar.gz` mit `.json`). Bei von Hand abgelegten Dateien gibt es keinen Knopf, sie
  bleiben lokal. Sie haben keine Begleitdatei, die nach dem Löschen im Katalog stehen bliebe.
- `POST /api/admin/archive/entries/drop-local` mit `{"paths": [...]}` oder `{"all_verified": true}`.
  Antwort 202 mit `job_id`. Es läuft als Auftrag `drop_local` in der vorhandenen Reihe, mit Fortschritt
  unter „Laufende Vorgänge“, weil das Zurücklesen großer Pakete dauert.
  - Server nicht aktiv → 409 `archive_remote_inactive`. Ein Pfad ist nicht `<art>/<datei>.tar.gz` → 400.
  - Ein genannter Pfad ist nicht „verified“ → 409 `archive_not_on_server`, es wird nichts eingereiht.
- **Je Paket, unmittelbar vor dem Löschen:**
  1. Das Paket vom Server **vollständig zurücklesen** und das sha256 mit der lokalen `.json`
     vergleichen. Das ist strenger als nur Größe und sha256 aus der Server-`.json` (Plan 13.10.), aber
     nur so ist sicher, dass die Kopie wirklich lesbar ist.
  2. Die Server-`.json` lesen, ihr sha256 muss gleich sein.
  3. Erst die lokale `.json` auf `remote.state = "remote_only"` setzen, dann die lokale `.tar.gz`
     entfernen. Bricht es dazwischen ab, setzt `recover()` den Stand für Pakete, deren Datei noch da
     ist, auf „verified“ zurück. So geht nichts verloren und nichts steht falsch in der Liste.
  - Weicht etwas ab oder fehlt auf dem Server: Das Paket bleibt lokal, der Stand geht auf „wartet“,
    und es kommt neu in die Kopier-Reihe. Die übrigen Pakete laufen weiter. Ist der Server gleich zu
    Beginn nicht erreichbar, endet der Auftrag mit `unreachable`, und es wird nichts gelöscht.
- **Katalog:** Pakete mit `remote_only` stehen weiter in der Liste („nur auf dem Server“,
  `local: false`). Sie zählen beim belegten Platz nicht mehr mit. Abgleich und Umzug (1b) lassen
  sie unberührt, nur die `.json` zieht mit um.
- **Fenster:** Pro Paket mit Stand „auf dem Server“ gibt es einen Knopf „Lokale Kopie löschen“. Im
  Bereich „Externer Server“ gibt es „Alle lokalen Kopien löschen (Anzahl, Größe)“. Beides öffnet einen
  Dialog mit Ort der Server-Kopie und frei werdendem Platz, ohne Namen-Eintippen.

### Was nicht in Etappe 3 kommt

- Andere Ziele als SMB (SFTP, S3) – das Muster bleibt offen dafür.
- Löschen auf dem Server aus HydraHive heraus. Der Server ist das
  Langzeit-Archiv, aufgeräumt wird dort von Hand oder später.
- Das Archiv-Laufwerk „Ort wechseln“ (Etappe 1b) bleibt lokal.

### API

- `GET/PUT /api/admin/archive/remote` (Einstellungen, ohne Passwort),
  `POST /api/admin/archive/remote/test`, `POST /api/admin/archive/remote/sync`
  (Abgleich), `POST /api/admin/archive/entries/drop-local`
  (`{"paths": [...]}` oder `{"all_verified": true}`, 202 als Auftrag).
- `GET /api/admin/archive/status` bekommt `remote`: eingetragen, aktiv,
  erreichbar, freier Platz, Pakete wartend/auf dem Server/nur lokal,
  letzter Fehler.

### Tests (zuerst rot)

- Ein SMB-Server im Test: ein `FakeRemote` mit derselben Schnittstelle
  (`put`, `get`, `stat`, `list`, `remove`), der in einen Ordner schreibt.
  Dazu ein Test gegen die echte Bibliothek, wenn `HH_TEST_SMB_URL` gesetzt
  ist (in der CI übersprungen, auf hydratest echt).
- Einstellungen: Passwort nie in der Antwort, verschlüsselt in der Datei,
  leeres Feld behält das alte, ungültige Namen → 400.
- Kopieren: Paket kommt hoch, Prüfsumme gelesen und verglichen; Server weg
  → bleibt in der Reihe, kein Fehler beim Löschen; Neustart mitten im
  Hochladen; Abgleich findet alte Pakete.
- Lokale Kopie löschen: nur mit geprüfter Server-Kopie; Server weg → 409;
  sha256 auf dem Server anders → 409 und nichts gelöscht; danach „nur
  Server“ in der Liste.
- E2E auf hydratest gegen eine echte Samba-Freigabe; frischer
  `images:ubuntu/26.04`-Container ohne Samba (Abhängigkeit kommt per pip).

### Funde beim Bau 3a (14.10.)

- **Samba erlaubt `replace` über eine bestehende Datei nicht** (ACCESS_DENIED, gemessen auf hydratest).
  Darum: alte Datei erst entfernen, dann `.part` umbenennen. Die Lücke dazwischen ist unkritisch: Die
  Kopie gilt erst nach dem Zurücklesen als „auf dem Server“.
- **Fehler-Codes von Samba**: Datei fehlt = `0xC0000034`/`0xC000003A`, Freigabe unbekannt =
  `0xC00000CC`/`0xC0000225`. `SMBOSError` erbt von `OSError` und darf nie als „nicht erreichbar“ gelten.
- **Die Archiv-Freigabe hat einen Papierkorb**: Was HydraHive auf dem Server ersetzt oder löscht, landet
  dort (gesehen beim Test gegen hydratest). Das ist so gewollt (Etappe 1) – für ein NAS ohne Papierkorb
  ändert sich nichts.
- Unterordner mit führendem „/“ (wie beim Projekt-Laufwerk, `/hydrahive`) wird still bereinigt.

### PRs

1. **3a**: Einstellungen, Verbindungstest, Kopier-Reihe, Abgleich, Anzeige.
2. **3b**: Lokale Kopie löschen.

**Offene Frage an Till:** Soll der Server-Bereich auch Prods
Einstellungen vorbelegen? (Nein ist die Empfehlung: Es gibt keine
geheime Ab-Werk-Konfiguration, jeder trägt sein NAS selbst ein.)
