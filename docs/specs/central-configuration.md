# Zentrale Konfiguration — ein Ort für alle Einstellungen

Status: **Entwurf — Grundrichtung freigegeben (Till, 26.09.2026), Details offen**

Verwandte Spec: `agent-infrastructure-tools.md` (Container und VMs). Deren
Datenmodell für Maschinen, Adressen und MACs ist hier Teil der System-Ebene.

## 1. Problem

Einstellungen sind über viele Orte verteilt. Ein großer Teil ist nur per Shell
sichtbar oder änderbar, für Admins wie für Nutzer. Fehler bleiben dadurch
wochenlang unbemerkt. Beispiele allein vom 26.09.2026:

| Fehler | Dauer | Wo er sichtbar gewesen wäre |
|---|---|---|
| Websuche (SearXNG) abgestürzt, 364.199 Neustarts | 4 Wochen | Dienste: Status |
| Adressen eines abgeschalteten Netzes in Gitea, Webmin, Extensions, MCP | Monate | Netzwerk: Adresse nicht erreichbar |
| Kontextfenster neuer Modelle 32k statt 1M | seit Modellstart | Modelle: Fenster unbekannt |
| Standard-Auswahl zeigt „Auswählen…" trotz gesetztem Modell | unbekannt | Modelle: Standard nicht in Liste |
| Container läuft, HydraHive zeigt „Fehler" | seit 25.09. | Container: Zustand widersprüchlich |
| Whisper-Modell im Installer ≠ auf dem Server | unbekannt | Abweichung vom Soll |

Zusätzlich haben Nutzer keinen Einfluss auf Dinge, die sie direkt betreffen,
etwa wohin ihre generierten Bilder, Videos und Musikstücke gespeichert werden.

## 2. Ziel

- **Ein Zugriffspunkt:** Jede Einstellung ist an genau einer Stelle der
  Oberfläche zu finden, mit ihrem aktuellen Wert, ihrer Herkunft und ihrem
  Zustand.
- **Prüfbar:** Zu jeder Einstellung lässt sich feststellen, ob sie fehlt, ob sie
  falsch ist (nicht erreichbar, abgelaufen, widersprüchlich) oder ob sie stimmt.
- **Nach Rolle getrennt:** Admins verwalten das System, Nutzer ihren eigenen
  Bereich, Projekt-Eigentümer ihre Projekte.
- **Geführt:** Ein Assistent führt bei der Ersteinrichtung und bei einer
  laufenden Installation durch alles, was fehlt oder falsch ist.
- **Ohne Shell:** Alles, was ein Admin oder Nutzer regulär ändern muss, geht
  über die Oberfläche.

## 3. Bestandsaufnahme (Stand 26.09.2026)

Erhoben auf der Entwicklungsinstallation. Nur Umfang und Art, keine Werte.

### 3.1 System

| Bereich | Umfang | Speicherort | Oberfläche |
|---|---|---|---|
| Grundeinstellungen | 83 Umgebungsvariablen `HH_*` im Code | systemd-Unit, `/etc/hydrahive2/env` | fast nicht |
| Systemeinstellungen | 19 Einträge (`settings/editable.py`) | `/etc/hydrahive2/overrides.json` | ja |
| LLM-Anbieter, Standard-Modelle | Anbieter + 7 Standards | `/etc/hydrahive2/llm.json` | ja |
| Weitere Systemdateien | 28 Dateien (Nutzer, API-Keys, MCP, Extensions, Gitea, Messenger, TLS, Samba, Matrix, Compute-PKI …) | `/etc/hydrahive2/` | teilweise |
| Hintergrunddienste | 24 systemd-Units/-Timer | systemd | nein |
| Fremddienste | Gitea, SearXNG, Pi-hole, Voice-Bridge, STT-/TTS-Container | jeweils eigene Konfiguration | nein |
| Container, VMs | 12 Container, 0 VMs | Incus, HydraHive-DB (unvollständig) | teilweise |
| Hardware | Platten, GPU, Netzwerk, USB, seriell | — | nur Passthrough-Kandidaten |

### 3.2 Benutzer

| Bereich | Umfang | Speicherort | Oberfläche |
|---|---|---|---|
| Konto | 3 Felder (Passwort-Hash, Rolle, ID) | `/etc/hydrahive2/users.json` | ja |
| Zugangsdaten | Profile je Nutzer (bearer, basic, ssh_key) | `credentials/<nutzer>.json` | ja |
| Vorlieben | ein JSON-Block je Nutzer | DB `user_preferences` | teilweise |
| Browser-Einstellungen (z. B. Vorlese-Stimme) | — | `localStorage` | nur auf dem Gerät |
| Eigener Workspace | **gibt es nicht** — nur Projekt-, Spezialisten- und Master-Workspaces je Agent | — | — |

### 3.3 Projekte und Agenten

| Bereich | Umfang | Auffälligkeiten |
|---|---|---|
| Agent (`agents/<id>/config.json`) | 37 Felder | 5 verwaiste Felder, die in Configs stehen, aber von keinem Code gelesen werden: `memory_crystal_scope`, `memory_max_chars`, `memory_max_crystals`, `memory_max_lessons`, `memory_min_lesson_confidence` |
| Projekt (`projects/<id>/config.json`) | 21 Felder | `webhook_secret` wird von Butler-Webhooks geprüft, ist aber nirgends einstellbar. `git_repos` und `samba_enabled` haben eigene Oberflächen (Git-Panel, Samba-Abschnitt). |

Verwaiste Felder sind ebenfalls ein Befund: Die Übersicht soll Werte zeigen,
die gespeichert sind, aber nichts bewirken.

### 3.4 Module

- 22 installierte Module, **keines** beschreibt seine Einstellungen.
- Werte liegen in eigenen DB-Tabellen (61 Modul-Tabellen, z. B.
  `module_rom_config`, `module_opentor_config`) oder in Umgebungsvariablen
  (z. B. 6 `HH_MEDIACENTER_*` mit Server-Adressen).
- Fest eingetragene absolute Pfade sind selten (9 Stellen, fast alle Telefonie);
  die meisten Module fragen HydraHive nach ihrem Datenordner.

### 3.5 Speicherorte für erzeugte Medien

| Erzeuger | Ziel heute | wählbar? |
|---|---|---|
| Agent-Tools (Bild, Video, Musik, Sprache) | `<Workspace des Agenten>/generated/` | nein |
| Videoeditor | `uploads/`, `exports/`, `generated/` | nein |
| Musicplayer | eigene Bibliothek + Import aus `generated/` | nein |
| Mediacenter | Download-Dienste auf dem NAS, Ziel HydraHive unbekannt | nein |

Bestehende Anbindung externer Speicher: **SMB-Mounts** (`smbmounts/`), je
Projekt, mit Eigentümer, Zugangsdaten, Nur-Lesen und Zustand. Andere Protokolle
gibt es nicht.

## 4. Grundprinzip: Jede Einstellung ist einmal beschrieben

Die Oberfläche, die Prüfungen und der Assistent werden aus einer Beschreibung
erzeugt, nicht für jede Einstellung einzeln programmiert. Das Vorbild ist
`settings/editable.py`; es wird zum allgemeinen Format.

Eine Beschreibung enthält:

| Feld | Bedeutung |
|---|---|
| `key` | eindeutiger Name, z. B. `system.websearch.url`, `module.mediacenter.sab_origin` |
| `scope` | `system`, `module`, `user`, `project`, `agent` |
| `type` | `string`, `int`, `bool`, `secret`, `url`, `path`, `storage_target`, `model`, `enum`, `list` |
| `label`, `help`, `group` | Anzeige und Gliederung |
| `default` | Standardwert |
| `required` | Pflicht? Optional abhängig von einer anderen Einstellung („nur wenn Mail aktiv") |
| `source` | Wo der Wert liegt: `overrides`, `env`, `file:<pfad>#<feld>`, `db:<tabelle>`, `external:<dienst>` |
| `editable` | `ui`, `ui_admin`, `readonly` (z. B. Grundeinstellungen, die vor dem Start feststehen müssen) |
| `check` | Name einer Prüfung (Abschnitt 6) |
| `sensitive` | Wert wird nie an den Browser gegeben, nur „gesetzt / nicht gesetzt" |

### 4.1 Module

Module beschreiben ihre Einstellungen im Manifest unter `settings`, im selben
Format mit `scope: module` oder `scope: user`. HydraHive liest die Beschreibung
bei der Installation. Ohne sie kann nicht geprüft werden, ob ein Modul
vollständig eingerichtet ist; Module ohne Beschreibung werden in der Übersicht
als „Einstellungen unbekannt" markiert.

### 4.2 Was gespeichert wird, bleibt, wo es sinnvoll ist

**Ein Zugriffspunkt heißt nicht eine Datei.**

- **Geheimnisse** (Passwörter, Keys, Tokens) bleiben getrennt, mit strengen
  Dateirechten, und verlassen den Server nie im Klartext.
- **Grundeinstellungen** (Datenordner, Port, Geheimschlüssel) müssen vor dem
  Start feststehen. Die Oberfläche zeigt sie an, ändern geht nur mit Neustart
  und nur für Admins, vorerst gar nicht.
- **Fremddienste** behalten ihre eigene Konfiguration. HydraHive liest und
  prüft sie. Schreiben darf es nur dort, wo es den Dienst selbst eingerichtet
  hat (z. B. Gitea-URL, SearXNG-venv).

## 5. Ebenen und Rechte

| Ebene | Wer ändert | Inhalt |
|---|---|---|
| **System** | Admin | Netzwerk und Adressen, Dienste, Hardware, Container/VMs, Anbieter und Standard-Modelle, Grundeinstellungen, Update |
| **Modul** | Admin; Teile, die ein Modul als `scope: user` markiert, der Nutzer | Server-Adressen, Speicherorte, Aktivierung |
| **Benutzer** | der Nutzer selbst | eigene Zugangsdaten, Stimme und Sprache, eigene Speicherziele, Benachrichtigungen |
| **Projekt** | Eigentümer, Mitglieder je nach Rolle | Modelle, Git-Repos, Freigaben, Speicherziele des Projekts |
| **Agent** | Eigentümer des Agenten | Modell, Werkzeuge, Gedächtnis-Grenzen |

Einstellungen, die bisher nur im Browser liegen (z. B. Vorlese-Stimme),
wandern in die Benutzer-Ebene, damit sie auf jedem Gerät gelten.

## 6. Prüfungen

Eine Prüfung liefert einen von vier Zuständen:

| Zustand | Bedeutung |
|---|---|
| `ok` | gesetzt und funktioniert |
| `missing` | Pflicht, aber nicht gesetzt |
| `invalid` | gesetzt, aber falsch (nicht erreichbar, abgelaufen, widersprüchlich) |
| `unknown` | nicht prüfbar (keine Prüfung hinterlegt, Dienst aus) |

Beispiele für Prüfungen:

| Prüfung | Was sie tut |
|---|---|
| `reachable` | Adresse/Port antwortet (mit kurzem Timeout, SSRF-geprüft) |
| `stale_network` | Adresse liegt in einem Netz, in dem der Server nicht mehr hängt |
| `service_running` | systemd-Unit aktiv, keine Neustart-Schleife |
| `model_available` | Modell steht in der Registry, Kontextfenster bekannt |
| `listed_default` | gespeicherter Standard ist in der Auswahlliste (siehe #445) |
| `credential_works` | Zugang wird vom Dienst akzeptiert |
| `storage_writable` | Speicherziel ist erreichbar und beschreibbar, genug Platz |
| `drift` | Wert auf dem Server weicht vom Soll des Installers ab |
| `orphaned` | Wert ist gespeichert, aber keine Beschreibung und kein Code nutzt ihn |

Prüfungen laufen auf Anfrage und regelmäßig im Hintergrund. Ergebnisse werden
kurz zwischengespeichert, damit die Übersicht schnell lädt.

## 7. Speicherziele

Ein Speicherziel ist ein benannter Ort, an dem Dateien abgelegt werden:

| Art | Beschreibung |
|---|---|
| `workspace` | Unterordner im eigenen Workspace (Standard, wie heute `generated/`) |
| `smb` | SMB/CIFS-Freigabe, baut auf `smbmounts/` auf |
| `sftp` | SFTP-Server |
| `ftp` | FTP/FTPS-Server |
| `webdav` | WebDAV (z. B. Nextcloud) |
| `s3` | S3-kompatibler Objektspeicher (später) |

- Nutzer legen eigene Speicherziele an, mit eigenen Zugangsdaten aus ihrem
  Zugangsdaten-Bereich. Admins können Ziele für alle bereitstellen.
- Pro Nutzer und optional pro Projekt wird festgelegt, welches Ziel für welche
  Art Ergebnis gilt: Bilder, Videos, Musik, Sprache, Exporte.
- Medien-Tools und Module schreiben nicht mehr fest nach `generated/`, sondern
  fragen das zuständige Ziel ab. Ohne Einstellung bleibt es beim Workspace.
- **Die Oberfläche braucht weiterhin Zugriff zum Anzeigen.** Bei entfernten
  Zielen wird zusätzlich eine kleine Vorschau oder ein Verweis im Workspace
  abgelegt, damit Chat und Galerie das Ergebnis zeigen können.
- **Sicherheit:** Ziele werden gegen SSRF geprüft (keine internen Dienste
  ansprechen, außer der Admin gibt sie frei). Zugangsdaten verlassen den Server
  nicht. Pfade werden gegen Ausbrüche aus dem Zielordner geprüft.

Offen: Ob FTP (unverschlüsselt) überhaupt angeboten wird oder nur FTPS/SFTP.

## 8. Oberfläche

### 8.1 Admin: Systemverwaltung

Gliederung nach Themen, jeweils mit Zustand:

- **Übersicht:** Zusammenfassung („3 Probleme, 5 Einstellungen fehlen"), Liste der offenen Punkte
- **Netzwerk und Adressen:** eigene Schnittstellen und Adressen, alle in Konfigurationen verwendeten Adressen mit Erreichbarkeit, Container/VMs mit IP und MAC
- **Dienste:** HydraHive, Websuche, Gitea, Voice, AgentLink, Hintergrund-Timer; Zustand und Neustart-Zähler
- **Modelle:** Anbieter, Standard-Modelle, nicht mehr verfügbare Modelle in Agenten-Configs
- **Module:** je Modul Einstellungen und Vollständigkeit
- **Speicher:** Platten, RAID, Belegung, Speicherziele
- **Hardware:** GPU, USB- und serielle Geräte, Netzwerkkarten; neu erkannte Geräte hervorgehoben
- **Container und VMs:** aus `agent-infrastructure-tools.md`
- **System:** Version, Updates, Grundeinstellungen (nur lesen)

### 8.2 Benutzer: Mein Bereich

- Zugangsdaten
- Speicherziele und Zuordnung (wohin Bilder, Videos, Musik …)
- Stimme, Sprache, Benachrichtigungen
- eigene Projekte und deren fehlende Einstellungen

### 8.3 Assistent

Nutzt dieselben Beschreibungen und Prüfungen. Er führt Punkt für Punkt durch
alles mit Zustand `missing` oder `invalid`, zuerst Pflichtfelder, dann
Empfehlungen. Bei der Ersteinrichtung in fester Reihenfolge, in einer
laufenden Installation nur durch das Offene.

## 9. Hardware

- Erkennung von Platten, GPU, Netzwerkkarten, USB- und seriellen Geräten.
- Ein neu angestecktes Gerät erscheint als „neu erkannt", mit Vorschlag, was
  damit möglich ist (z. B. „an Container durchreichen", „als Speicher
  einbinden").
- Keine automatische Aktion. Alles, was Hardware verändert (Formatieren,
  Einbinden, Durchreichen), braucht eine Bestätigung.

## 10. Abgrenzung

Nicht Teil dieser Spec:

- Ersatz der bestehenden Seiten für Agenten, Projekte, Anbieter. Sie bleiben;
  die Übersicht verlinkt auf sie und ergänzt fehlende Felder.
- Verschieben aller Einstellungen in eine gemeinsame Datei oder Datenbank.
- Änderungen an Grundeinstellungen über die Oberfläche (vorerst nur lesen).
- Verwaltung der FritzBox/des Routers.

## 11. Etappen

Jede Etappe ist für sich nutzbar.

1. **Beschreibungsformat und Prüfungen** für die Bereiche, in denen am
   26.09.2026 Fehler auftraten: Netzwerk/Adressen, Dienste, Standard-Modelle.
2. **Admin-Übersicht, nur lesen:** alles sehen, Probleme markiert.
3. **Module beschreiben ihre Einstellungen** im Manifest; Vollständigkeit je Modul.
4. **Ändern über die Oberfläche** für System- und Modul-Einstellungen, mit
   Prüfung vor dem Speichern.
5. **Benutzer-Bereich** inklusive Browser-Einstellungen auf den Server.
6. **Speicherziele:** Workspace und SMB zuerst, dann SFTP/WebDAV/FTPS;
   Medien-Tools auf Ziele umstellen.
7. **Hardware-Erkennung.**
8. **Assistent** für Ersteinrichtung und offene Punkte.
9. **Aufräumen:** `webhook_secret` einstellbar machen; verwaiste Agent-Felder
   entweder anbinden oder aus den Configs entfernen.

## 12. Offene Punkte

- FTP unverschlüsselt anbieten oder nur FTPS/SFTP?
- Speicherziele pro Projekt zusätzlich zu pro Nutzer, und wer gewinnt bei beidem?
- Kontingent für Speicher im Workspace (Plattenplatz je Nutzer)?
- Braucht es einen eigenen Nutzer-Workspace (heute gibt es nur Projekt-,
  Spezialisten- und Master-Workspaces je Agent)?
- Wie oft laufen Hintergrund-Prüfungen, und wer wird bei neuen Problemen
  benachrichtigt (nur Dashboard, Mail, Messenger)?
- Dürfen Nutzer Speicherziele im eigenen Netz (z. B. NAS) anlegen, obwohl die
  SSRF-Prüfung private Adressen sperrt? Vorschlag: Admin gibt Netze frei.
- Reihenfolge der Etappen 5–9 nach Etappe 4.

## 13. Akzeptanzkriterien (Gesamtvorhaben)

- [ ] Jede Einstellung aus Abschnitt 3 ist in der Oberfläche auffindbar, mit
      Wert (bei Geheimnissen nur gesetzt/nicht gesetzt), Herkunft und Zustand.
- [ ] Die Fehler aus Abschnitt 1 würden in der Übersicht als `invalid` oder
      `missing` erscheinen (Regressionstest je Fall).
- [ ] Ein Nutzer kann ohne Shell festlegen, wohin seine Bilder, Videos und
      Musik gespeichert werden, und das Ziel wird vor dem Speichern geprüft.
- [ ] Ein Modul mit `settings` im Manifest zeigt seine Vollständigkeit an; ein
      Modul ohne wird als „Einstellungen unbekannt" markiert.
- [ ] Geheimnisse erscheinen nie im Klartext im Browser oder in Logs.
- [ ] Ein Nutzer sieht und ändert nur seine eigene Ebene sowie Projekte, in
      denen er Rechte hat.
