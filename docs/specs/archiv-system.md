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
> werden soll oder wohin er gespeichert werden soll. Vielleicht wäre ein
> Download ganz gut, wenn kein Server verfügbar ist, denn sonst können User
> ja keine Projekte löschen, wenn sie keinen extra Server haben.

Gilt für Agent, Projekt und Nutzer. Löschen geht nicht mehr mit einem Klick,
sondern über einen Dialog mit drei Wegen:

| Weg | Wann wählbar | Was passiert |
|---|---|---|
| **Ins Archiv** | Archiv eingerichtet **und** erreichbar | Packen, ins Archiv schreiben, Prüfsumme vergleichen, erst dann löschen |
| **Herunterladen, dann löschen** | immer (bis zur Größengrenze, s. u.) | Paket bauen, Browser lädt herunter, erst nach Bestätigung „Datei ist gespeichert“ löschen |
| **Unwiderruflich löschen** | immer | wie heute, aber nur nach Eintippen des Namens |

- Voreinstellung: „Ins Archiv“, wenn verfügbar, sonst „Herunterladen“.
  „Unwiderruflich“ ist nie vorausgewählt.
- Ist ein Archiv eingerichtet, aber gerade **nicht erreichbar**, sagt der
  Dialog das ausdrücklich („NAS 192.168.178.3 nicht erreichbar“). Er bietet
  dann nur Download oder unwiderruflich an. Ohne Wahl wird nichts gelöscht.
- Der Dialog zeigt, was betroffen ist: Name, Größe, beim Projekt die Zahl
  der mitgelöschten Agenten und Sessions.
- Die API spiegelt das: `DELETE` ohne Angabe von `mode` ergibt `409
  delete_mode_required` mit den möglichen Wegen und der Größe. Ein Löschen
  „aus Versehen“ ohne Wahl, etwa über alte Oberflächen oder Skripte, ist
  damit ausgeschlossen.

### Download bei großen Daten

Befund Prod: Projekte bis **988 GB** („HDD Archive“ 988 GB, „hydrawow“ 126 GB,
„Hydrahive DEV“ 29 GB). Ein Browser-Download ist dafür nicht geeignet.
- Das Paket wird **gestreamt** (tar.gz direkt in die Antwort, keine Kopie auf
  der Platte), damit kein zweiter Plattenplatz in Projektgröße nötig ist.
- Eingehängte Laufwerke (z. B. `mounts/Hydrahive_backups`) werden nie mit
  eingepackt, sonst wanderte das NAS ins Paket.
- **Größengrenze** `HH_DELETE_DOWNLOAD_MAX_GB` (Einstellung, Standard 20 GB).
  Darüber ist „Herunterladen“ ausgegraut, mit Hinweis: „Zu groß für den
  Download, bitte Archiv einrichten oder Daten vorher selbst sichern.“
- Gelöscht wird erst, wenn der Download vollständig ausgeliefert ist **und**
  der Nutzer bestätigt. Bricht der Download ab, passiert nichts.

### Agenten selbst

Heute gibt es kein Werkzeug, mit dem ein Agent Agenten oder Projekte löscht.
Das bleibt so. Agent-Werkzeuge kommen erst in Etappe 5 und können nur
**ablegen**, nicht löschen.

## Etappen (angepasst)

1. **Speicher + Einstellungen:** wie oben, plus Verbindungstest.
2. **Lösch-Dialog mit drei Wegen** für Agent, Projekt und Nutzer: Archiv,
   gestreamter Download mit Größengrenze, unwiderruflich mit Namenseingabe.
   API `mode` Pflicht. Skript für die vorhandenen Waisen.
3. Projekt archivieren · 4. System-Backup ins Archiv · 5. Archiv-Ansicht +
   Agent-Werkzeuge · 6. Archiv als Wissen (unverändert).

Etappe 2 lässt sich auch ohne NAS sofort nutzen, mit Download oder
unwiderruflich. Damit endet das stille Löschen von Gedächtnis und
Arbeitsordnern schon vor Etappe 1, wenn man die Reihenfolge tauscht.

## Offene Frage (eine)

Reihenfolge: **zuerst Etappe 2** (Lösch-Dialog mit Download, beendet sofort
das stille Löschen, braucht kein NAS) **und dann Etappe 1** (Archiv-Speicher)?
Oder wie geplant 1 vor 2?
