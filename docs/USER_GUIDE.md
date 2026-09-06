# HydraHive Benutzerhandbuch

> **Für:** Anwender, Projektverantwortliche und Administratoren
> **Stand:** 2026-09-06
> **Funktionsstatus:** [FEATURES.md](FEATURES.md) · **Installation:** [installer/README.md](../installer/README.md)

HydraHive ist eine selbst gehostete Arbeitsoberfläche für KI-Agenten, Projekte, Automatisierung und Medienproduktion. Die HydraHive-Daten liegen auf dem eigenen Server. Wenn du ein Cloud-Modell oder einen externen Dienst verwendest, werden die dafür nötigen Daten trotzdem an diesen Anbieter übertragen.

Die sichtbaren Menüpunkte hängen von Rolle, installierten Modulen, aktivierten Integrationen und Bildschirmgröße ab. Die deutsche und englische Oberfläche können leicht abweichende Bezeichnungen verwenden.

---

## 1. Erste Anmeldung

Nach der Linux-Installation zeigt das Installationsskript:

- die HTTPS-Adresse des Servers;
- den Benutzernamen `admin`;
- das einmalig erzeugte Administrator-Passwort.

Rufe anschließend `https://<server-ip>` auf. Das standardmäßig selbst signierte Zertifikat verursacht zunächst eine Browserwarnung. Prüfe, dass Adresse und Zertifikat zu deinem Server gehören, bevor du die Ausnahme bestätigst.

Nach dem ersten Login:

1. ändere das Administrator-Passwort;
2. richte mindestens einen Modellanbieter oder ein lokales Modell ein;
3. prüfe unter **System/Integrationen**, welche optionalen Komponenten installiert wurden;
4. lege für den Alltag einen normalen Benutzer an, wenn nicht jede Person Administratorrechte benötigt;
5. aktiviere Tool-Bestätigungen für Agenten mit sensiblen System- oder Schreibwerkzeugen.

> Administratoren können Benutzer, Server, Erweiterungen und Systemdienste verwalten. Vergib diese Rolle sparsam.

---

## 2. Orientierung in der Oberfläche

Die wichtigsten Bereiche sind:

| Bereich | Zweck |
|---|---|
| **Buddy** | persönlicher Standard-Assistent |
| **Chats** | Unterhaltungen mit einem Agenten |
| **Agenten** | Agenten, Modelle, Fähigkeiten und Tools konfigurieren |
| **Läufe/Aufgaben** | aktive, wartende, abgeschlossene oder fehlgeschlagene Agentenläufe |
| **Projekte** | gemeinsame Workspaces, Repositories, Mitglieder, Agenten und Aufgaben |
| **Modelle / Provider** | Cloud- und lokale Modelle konfigurieren |
| **Medien** | generierte Bilder, Audio und Videos verwalten |
| **Prompt-Archiv** | wiederverwendbare Generierungsrezepte speichern |
| **Atelier / Video Editor** | Charaktere, Szenen, Storyboards und Videos vorbereiten |
| **Data Mining** | frühere Sessions durchsuchen und Aktivität auswerten |
| **Module / Themes / Plugins** | HydraHive erweitern |
| **Vault** | sensible Bereiche wie Akte, Crypto, Notizen, Credentials, Memory und Data Mining bewusst öffnen |
| **Administration** | Benutzer, Sicherheit, Logs, Updates und Infrastruktur |

Auf kleinen Bildschirmen liegen globale Aktionen in kompakten Menüs. Projektbezogene Aktionen erscheinen innerhalb des jeweiligen Projekt-Cockpits.

---

## 3. Mit Buddy und Agenten chatten

### Neue Unterhaltung

1. Öffne **Buddy**, **Chats** oder einen Agenten.
2. Erstelle eine neue Session oder wähle eine bestehende aus.
3. Gib die Aufgabe möglichst konkret ein.
4. Hänge bei Bedarf Dateien oder Bilder an.
5. Sende die Nachricht.

Antworten werden gestreamt. Während eines Laufs siehst du je nach Modell und Konfiguration:

- bereits erzeugten Text;
- Reasoning-/Statusinformationen;
- angeforderte Tool-Aufrufe;
- laufende, bestätigungspflichtige oder beendete Aktionen;
- Token- und Modellinformationen.

### Anhänge

Chatnachrichten können Dateien enthalten. Der Linux-Proxy begrenzt normale Chat-Uploads auf ungefähr 200 MiB Nutzdaten plus Multipart-Overhead. Andere Upload-Endpunkte, etwa ISO- oder Mediendateien, haben eigene Grenzen.

Ein Anhang kann in Modellkontext oder Werkzeugaufrufe einfließen. Prüfe vor dem Upload vertraulicher Dateien, ob das ausgewählte Modell lokal läuft oder ein Cloud-Anbieter ist.

### Tool-Bestätigungen

Ein Agent kann so eingestellt werden, dass Werkzeugaufrufe vor der Ausführung bestätigt werden müssen. Dann zeigt der Chat:

1. den Werkzeugnamen;
2. die beabsichtigten Parameter;
3. eine Schaltfläche zum Erlauben oder Ablehnen.

Lies insbesondere Shell-, Datei-, Server-, Download-, Mail- und Smart-Home-Aktionen vollständig. Eine Bestätigung gilt für die konkrete angezeigte Aktion, nicht pauschal für alle späteren Aufrufe.

### Stoppen, fortsetzen und neu laden

- **Stoppen** bricht den aktuellen Lauf ab.
- **Neu laden** verbindet sich wieder mit einem noch laufenden, abgekoppelten Lauf.
- **Fortsetzen** nimmt eine pausierte Session wieder auf, zum Beispiel nach Erreichen des Iterationslimits.
- **Erneut senden** startet einen neuen Versuch ab einer ausgewählten Nachricht.

HydraHive speichert Laufzustand und Nachrichten serverseitig. Ein geschlossenes Browserfenster muss einen abgekoppelten Lauf daher nicht beenden.

### Modell oder Reasoning pro Session ändern

Wenn freigeschaltet, kannst du im Chat für eine einzelne Session ein anderes Modell oder eine andere Reasoning-Tiefe auswählen. Diese Auswahl überschreibt die Agentenvorgabe nur für diese Session.

### Sessions organisieren

Du kannst Sessions erstellen, umbenennen, einem Projekt zuordnen, ihren Status ändern und löschen. Die Chat-Suche filtert geladene Nachrichten. Der lokale Befehl `/export` formatiert den aktuell geladenen Verlauf als Markdown im Chat; er erzeugt keinen vollständigen Server-Backup.

Die zuvor dokumentierten Archiv-, Tag- und Fork-Funktionen sind im aktuellen Core-Session-API nicht vorhanden. Löschen ist dauerhaft; nutze ein System-Backup, wenn der Verlauf erhalten bleiben soll.

---

## 4. Agenten konfigurieren

Ein Agent ist mehr als ein Chatprofil. Seine Konfiguration bestimmt, welches Modell, welcher Kontext und welche Werkzeuge verfügbar sind.

### Wichtige Felder

| Feld | Bedeutung |
|---|---|
| **Name und Beschreibung** | sichtbare Identität und Zweck |
| **System-Prompt** | dauerhafte Verhaltens- und Aufgabenanweisung |
| **Primärmodell** | Standardmodell für Antworten |
| **Fallback-Modelle** | Alternativen bei Fehlern des Primärmodells |
| **Kompaktierungsmodell** | optionales Modell für Zusammenfassungen langer Sessions |
| **Temperatur** | Zufälligkeit/Kreativität, soweit vom Anbieter unterstützt |
| **Max Tokens** | maximales Ausgabe-Budget pro Modellaufruf |
| **Reasoning** | gewünschte Denktiefe, soweit vom Modell unterstützt |
| **Max Iterationen** | Anzahl Modell-/Werkzeugrunden vor einer Pause |
| **Tools** | erlaubte native oder Plugin-Werkzeuge |
| **MCP-Server** | zusätzliche Werkzeuge externer MCP-Dienste |
| **Skills** | wiederverwendbare Anleitungen |
| **Langzeitgedächtnis** | erlaubt Recall und Memory-Karten |
| **Bestätigung erforderlich** | hält Tool-Aufrufe bis zur Freigabe an |

Nicht jedes Modell unterstützt jedes Feld. HydraHive blendet Optionen nach Möglichkeit passend ein; der Anbieter kann dennoch eine Einstellung ignorieren oder ablehnen.

### Buddy, Projektagenten und Spezialisten

- **Buddy** ist der persönliche Standard-Assistent eines Benutzers.
- **Persönliche Agenten** arbeiten im eigenen Agenten-Workspace.
- **Projektagenten** erhalten Zugriff auf den Workspace eines Projekts.
- **Spezialisten** gehören zu einem Projekt oder übergeordneten Agenten und können über AgentLink beauftragt werden.

Ein Agent bekommt nicht automatisch Zugriff auf andere Projekte oder Benutzerressourcen.

### Agenten-Konfigurationsumfang

Der aktuelle Core bietet Agenten-CRUD, System-Prompt, Soul-/Markdown-Komponenten, Vorlagen, Tools, MCP und Skills. Ein allgemeiner Agenten-Import/-Export-Endpunkt ist im aktuellen API nicht vorhanden; sichere Konfigurationen deshalb über den normalen System-/Datei-Backup-Pfad.

---

## 5. Skills, MCP und Plugins

### Skills

Ein Skill ist eine wiederverwendbare Markdown-Anleitung mit Beschreibung und Aktivierungsregel. Skills können global, projektweit oder nur für einen Spezialisten gelten.

Gute Skills enthalten:

- wann sie verwendet werden sollen;
- eine klare Schrittfolge;
- Sicherheits- und Bestätigungsregeln;
- erwartete Ein- und Ausgaben;
- Verifikationsschritte.

Deaktiviere einen Skill für einen Agenten, wenn er dessen Aufgabe stört oder unnötig Kontext verbraucht.

### MCP-Server

MCP-Server stellen externe Werkzeuge bereit. HydraHive unterstützt konfigurierte MCP-Verbindungen; tatsächlich sichtbare Werkzeuge hängen von Serverstatus und Agentenzuweisung ab.

Vor der Freigabe:

1. prüfe URL/Befehl und Betreiber;
2. hinterlege nötige Credentials in HydraHive statt im Prompt;
3. teste die Verbindung;
4. weise nur die benötigten Werkzeuge zu.

### Plugins

Plugins sind lokal installierte Agentenwerkzeuge. Sie laufen als Subprozess mit eingeschränkter Umgebung, aber nicht in einer vollständig sicheren Sandbox. Installiere nur geprüften Code und gib Plugins nur den Agenten, die sie benötigen.

---

## 6. Projekte

Ein Projekt bündelt Arbeitsdaten und Zusammenarbeit:

- Mitglieder und Rollen;
- einen isolierten Workspace;
- Repositories;
- Projektagenten und Spezialisten;
- projektgebundene Aufgaben aus dem Tasks-Modul;
- Sessions, Statistiken und Audit-Ereignisse;
- Dateien und Medien;
- optional VM-/Container-Zuordnung, Mounts, Integrationen und einen Code-Graphen.

### Projekt anlegen

1. Öffne **Projekte**.
2. Wähle **Neues Projekt**.
3. Vergib Name und Beschreibung.
4. Füge Mitglieder und Rollen hinzu.
5. Verknüpfe vorhandene Repositories oder lege sie über GitHub/Gitea an.
6. Erstelle anschließend Agenten und Spezialisten für konkrete Aufgaben.

### Mitglieder und Rollen

Der Projekteigentümer verwaltet Mitgliedschaft und Projektrollen. Entferne Personen nur, wenn geklärt ist, wem offene Sessions, Aufgaben oder externe Zugänge gehören. Globale Administratorrechte ersetzen nicht die fachliche Verantwortung des Projekteigentümers.

### Dateien

Im Dateibereich kannst du:

- Verzeichnisse durchsuchen;
- Dateien anzeigen und bearbeiten;
- Dateien hoch- und herunterladen;
- neue Dateien/Ordner anlegen;
- Dateien löschen;
- konfigurierte SMB-Mounts verwenden.

Dateiwerkzeuge eines Projektagenten arbeiten standardmäßig relativ zum Projekt-Workspace. Absolute Pfade oder Serverwerkzeuge können weiterreichende Rechte haben und sollten nur gezielt erlaubt werden.

### Git und Repositories

HydraHive zeigt Repository-Status und unterstützt Git-Aktionen. Für private Remotes muss ein passendes Credential-Profil oder Projekt-Token eingerichtet sein.

Vor Commit oder Push:

1. prüfe `git status` und Diff;
2. stelle nur beabsichtigte Dateien bereit;
3. führe projektbezogene Tests aus;
4. verwende nachvollziehbare Commit-Nachrichten;
5. pushe erst nach erfolgreicher Prüfung.

### Projektaufgaben

Das Aufgabenboard nutzt das erforderliche Tasks-Modul. Es unterstützt Titel, Priorität, Projektbezug und die Statuswerte `open`, `in_progress`, `done` und `cancelled`. Der aktuelle Core enthält weder Aufgabenkommentare noch GitHub-Issue-Synchronisation.

### Code-Graph

Der Code-Graph hilft bei Fragen wie:

- „Was ruft diese Funktion auf?“
- „Welche Dateien sind von einer Änderung betroffen?“
- „Wie hängen zwei Symbole zusammen?“
- „Erkläre diesen Knoten.“

Der Graph muss zuerst für die gewünschten Verzeichnisse gebaut werden. Nach Codeänderungen ist ein Refresh nötig; sonst beziehen sich Ergebnisse auf den letzten Build.

### Integrationen, Mounts und Laufzeitzuordnung

Im Projekt-Cockpit können je nach Projektrolle MCP-Server-IDs, erlaubte Plugins, ein Projekt-LLM-Key, Samba, SMB-Mounts sowie VMs/Container zugeordnet werden. Die Zuordnung ändert den Projektbezug; sie ersetzt keine Ressourcenlimits des Hosts oder Providers. Ein allgemeines Projektbudget-System ist im aktuellen Core nicht vorhanden.

---

## 7. Modelle und Provider

### Cloud-Provider

HydraHive enthält direkte Katalog-/Konfigurationspfade für Anthropic, OpenAI, OpenAI Codex OAuth, OpenRouter, Groq, Mistral, Google Gemini, NVIDIA NIM, MiniMax und Ollama. Modelle weiterer Anbieter können über Aggregatoren wie OpenRouter oder NVIDIA NIM erscheinen; das ist kein eigener direkter Provider-Adapter.

Zum Einrichten:

1. öffne **Modelle** oder **Provider**;
2. wähle den Provider;
3. hinterlege API-Key, OAuth-Verbindung oder Basis-URL;
4. aktualisiere den Modellkatalog;
5. teste ein Modell zunächst mit einem unkritischen Prompt;
6. weise es anschließend einem Agenten zu.

Die angezeigten Kosten sind Schätzungen auf Basis der hinterlegten Preismetadaten und gemessenen Tokens. Die Providerrechnung ist maßgeblich.

### Lokale Modelle

Für Ollama-kompatible Laufzeiten gibt es Modellbestand, Pull/Löschen und Laufzeitaktionen. Wenn `llmfit` installiert ist, zeigt HydraHive eine Hardware-Eignungsschätzung.

Eine Eignungsschätzung garantiert weder Geschwindigkeit noch Stabilität. Kontextgröße, Quantisierung, parallele Nutzer und GPU-Offloading verändern den tatsächlichen Speicherbedarf.

### Fallbacks

Fallback-Modelle werden in Reihenfolge verwendet, wenn der primäre Aufruf in einem unterstützten Fehlerfall scheitert. Nutze nur Modelle, denen derselbe Prompt- und Datenkontext anvertraut werden darf.

---

## 8. Medien, Prompt-Archiv, Atelier und Video Editor

### Mediengenerierung

HydraHive kann je nach konfiguriertem Anbieter erzeugen oder verarbeiten:

- Bilder;
- Musik;
- Sprache/Voiceover;
- Videos;
- Audiotranskriptionen.

Generierte Dateien erscheinen in Medienansichten und können einem Projekt zugeordnet sein. Videojobs laufen häufig asynchron; die Dauer hängt vom Anbieter ab.

### Lokale Medienmodelle

Auf kompatiblen NVIDIA/CUDA-Systemen kann der Installer lokale Bild-/Videomodelle vorbereiten. Modelle müssen separat installiert und benötigen erheblichen Speicher. Wenn kein kompatibler Worker verfügbar ist, bleibt die lokale Option deaktiviert oder meldet einen Infrastrukturfehler.

### Prompt-Archiv

Speichere gute Generierungsrezepte mit:

- Titel und Kategorie;
- variablem Prompt;
- festem Stil-Anker;
- Modell und Parametern;
- Tags und Notizen;
- optionalem Beispielmedium.

Für konsistente Bildserien ist der Stil-Anker konstant zu halten; Motiv und Szene gehören in den variablen Teil.

### Atelier

Atelier ist ein Modul aus dem offiziellen Hub und hängt vom Video-Editor-Modul ab; die Modulverwaltung installiert die Abhängigkeit zuerst. Das Atelier organisiert kreative Projekte:

1. Projekt/CI mit Stil-Anker, Palette und Format einrichten;
2. Charaktere mit Beschreibung, Modell, Seed und Referenzen anlegen;
3. Drehbuchkopf und Szenen definieren;
4. Dialoge, Emotion, Kamera, Ort, Tageszeit und Musik je Szene festlegen;
5. Bildmaterial generieren und in der Galerie prüfen;
6. geeignete Szenen an die Videoerstellung übergeben.

Nicht jede Modellkombination unterstützt Seeds, Referenzbilder oder jedes Seitenverhältnis gleich zuverlässig.

### Video Editor

Der Video Editor verwaltet Projekte, Assets, Timeline, Trimmen/Teilen, Transkription und Renderjobs. Große Quelldateien und Exporte benötigen ausreichend lokalen Speicher und ffmpeg-Unterstützung.

---

## 9. Integrierte Arbeitsbereiche

Der Core und der offizielle Modul-Hub stellen zusätzliche Arbeitsbereiche bereit:

- **Butler (Core):** Trigger-/Bedingungs-/Aktions-Flows, Dry-Run und Projekt-Webhooks;
- **Zahnfee (Core/Admin):** Dental-Labor- und Auftragsworkflow;
- **Streaming (Core):** Ghostflix-Serienauswahl und Downloadjobs in einen Plex-Pfad;
- **Archiver:** Webseiten, Foren-Threads und Dokumente archivieren, diagnostizieren und reparieren;
- **Atelier + Video-Editor:** KI-Medienproduktion und browserbasierter Schnitt;
- **Blueprint:** visueller Node-Canvas für Layouts und Abläufe;
- **Brettspiele / Minigames:** Spiele und Ergebnis-/Highscore-Speicherung;
- **Cryptoboard:** Kurse, Watchlist, Portfolio, Trades, Wallets, Alerts, Indikatoren und News;
- **Deep Research:** mehrstufige, quellenbasierte Rechercheberichte;
- **Haushaltsbuch:** Haushalte, Buchungen, Budgets/Planung, Bankimport und experimenteller read-only Lidl-Plus-Sync;
- **Home Assistant:** Entitäten lesen, Templates rendern und Dienste ausführen;
- **Mediacenter:** profilgefilterte Suche und kontrollierte SABnzbd-Übergabe;
- **Musicplayer:** Playlist/Equalizer für hochgeladene oder erzeugte Musik;
- **Notizbuch:** persönliche Notizen;
- **Meine Akte:** strukturierte Akte, eGA/FHIR-Import und Apple-Health-Ansichten;
- **Scratchpad:** getrennte User- und Agenten-Notizzonen;
- **Aufgaben:** persistente persönliche und projektbezogene Tasks;
- **Voice:** Voicebox für den Home-Assistant-Voice-PE-Pfad.

Das Beispiel-Modul ist nur eine Entwicklungsvorlage. Ein sichtbarer Bereich kann zusätzliche Zugangsdaten, Datenimporte oder einen externen Dienst benötigen. Medizinische, finanzielle und Krypto-Funktionen ersetzen keine professionelle Beratung.

---

## 10. Integrationen und Kommunikationskanäle

### WhatsApp

Die Linux-Installation kann die Bridge automatisch einrichten. Pairing und Status werden in der Weboberfläche verwaltet. Ein getrenntes WhatsApp-Konto bzw. die von WhatsApp geforderte Kopplung ist nötig.

### Discord

Hinterlege Bot-Konfiguration und Token, teste die Verbindung und ordne eingehende Nachrichten dem gewünschten Agenten zu. Bot-Rechte auf dem Discord-Server begrenzen, was HydraHive dort sehen oder senden kann.

### Matrix-Teamchat

Der Teamchat nutzt Matrix. HydraHive kann mit einem vorhandenen Homeserver arbeiten; der Extension-/Installer-Bereich kann Tuwunel als separaten Dienst bereitstellen. Räume und Mitglieder werden nicht allein durch das Aktivieren der UI erzeugt.

### E-Mail

IMAP dient zum Lesen, SMTP zum Senden. Die Mailwerkzeuge verändern beim Lesen standardmäßig nicht den Gelesen-Status. Verwende anwendungsspezifische Passwörter, wenn der Mailanbieter sie anbietet.

### Smart Home

Home Assistant wird über URL und Token angebunden. Leseaktionen sind von Schaltaktionen zu unterscheiden. Bei mehrdeutigen Geräten sollte ein Agent zuerst die Entitäten auflisten, bevor er einen Dienst aufruft.

---

## 11. Module, Themes, Plugins und Extensions

Diese Begriffe sind nicht austauschbar:

| Typ | Was wird erweitert? | Typisches Risiko |
|---|---|---|
| **Modul** | HydraHive-Navigation, UI, API und optional Agententools | läuft als Teil der Anwendung |
| **Theme** | Erscheinungsbild | CSS-/Darstellungsfehler |
| **Plugin** | Agententools | lokaler Subprozess mit Tool-Fähigkeiten |
| **Extension** | externer Dienst/Systempaket | Installation kann Root-/Docker-Rechte verwenden |

### Module/Themes installieren

1. Öffne die Modul- bzw. Theme-Verwaltung.
2. Wähle die konfigurierte Registry/Quelle.
3. Prüfe Version, Mindest-Core-Version und Abhängigkeiten.
4. Starte die Installation und beobachte den Hintergrundjob.
5. Aktiviere das Paket und lade die Oberfläche neu.

Bei einem defekten Modul bleiben andere Module nach Möglichkeit verfügbar. Ein Backend-Neustart kann nötig sein, um entfernte Python-Module vollständig aus dem Prozess zu lösen.

### Extensions installieren

Extensions installieren Drittsoftware wie Gitea, Ollama, Plex, SearXNG oder Vaultwarden. Die genaue Auswahl steht in [FEATURES.md](FEATURES.md).

Da Installationsskripte privilegiert laufen können:

- nur als Administrator ausführen;
- Manifest und Skript vorher prüfen;
- Backup erstellen;
- Ports, Speicher und bestehende Dienste kontrollieren;
- Installationslog auf Fehler prüfen.

---

## 12. Vault

Vault ist ein offline-first Launchpad für sensible HydraHive-Bereiche: Patientenakte, Cryptoboard, Scratchpad, Credentials, Data Mining und Memory. Beim Öffnen startet es keine breite Suche, keinen Export und keine LLM-Auswertung; diese Aktionen bleiben bewusst getrennt.

Die derzeit angezeigte Angabe „gesperrt nach 15 min“ ist noch kein implementierter Hard-Lock. Die Seite bezeichnet Vault-Lock/Unlock, Dokument-/OCR-Konsolidierung und einen kontextgeschützten Vault-Chat ausdrücklich als weitere Ausbaustufen. Behandle den aktuellen Vault daher als Navigations- und Soft-Guard, nicht als zusätzliche kryptografische Sperre.

---

## 13. Server, Compute Nodes, VMs und Container

### Federation-Workstations

Administratoren können andere HydraHive/A2A-Workstations mit URL, Token und TLS-Prüfung registrieren, deren Card/Audit abrufen und Client-Konfigurationen mit API-Key, AgentLink- und optionalen Tailscale-Daten erzeugen. Das ist vom Compute-Node-Kanal getrennt.

### Compute Nodes

Ein Compute Node wird über Bootstrap/Enrollment mit dem HydraHive-Server verbunden. Der Standardpfad verwendet Client-Zertifikate. Prüfe nach der Einrichtung:

- Verbindungsstatus;
- letzte Heartbeat-Zeit;
- CPU/RAM/GPU-/Speicherwerte;
- laufende Workloads;
- Zertifikatsstatus.

Weitere Details: [compute-node-runbook.md](compute-node-runbook.md).

### VMs und Container

Auf kompatiblen Linux-Hosts können Administratoren libvirt-VMs und Incus-Container verwalten. Vor Start/Stop/Löschen:

1. prüfe laufende Workloads und Benutzer;
2. erstelle bei Bedarf Snapshot/Backup;
3. bestätige Ressourcenbedarf und Storage-Ziel;
4. beobachte Status und Logs nach der Aktion.

Diese Funktionen sind auf macOS oder Hosts ohne Virtualisierungs-/Container-Unterstützung nicht verfügbar.

---

## 14. Administration und Betrieb

### Benutzer

Administratoren können Benutzer anlegen, Rollen ändern, Passwörter zurücksetzen und Transfers/Löschungen verwalten. HydraHive verhindert, dass der letzte Administrator über den normalen Rollenwechsel entfernt wird.

### Credentials und API-Keys

- Credentials speichern Zugangsdaten für Provider, URLs, Hosts oder Dienste.
- Werte werden verschlüsselt gespeichert und in der Oberfläche maskiert.
- URL-/Host-Muster begrenzen, wohin ein Credential injiziert werden darf.
- API-Keys erlauben programmatischen HydraHive-Zugriff und sollten wie Passwörter behandelt werden.

Lösche oder rotiere ein Credential sofort, wenn es versehentlich in Chat, Log oder Repository gelangt ist.

### Logs und Fehler

Hilfreiche Linux-Befehle:

```bash
sudo systemctl status hydrahive2
sudo journalctl -u hydrahive2 -f
sudo systemctl status nginx
sudo tail -f /var/log/hydrahive2-update.log
```

In der Admin-Oberfläche stehen zusätzlich Audit-, Security-, Fehler-, Token- und Kostenansichten zur Verfügung.

### Updates

Ein Update kann aus der Oberfläche angefordert oder über den Installer ausgeführt werden. Der Updateprozess kann Quellcode, Python-Abhängigkeiten und Frontend-Build ändern und anschließend den Dienst neu starten.

Vor einem größeren Update:

1. Backup/Restore-Point erstellen;
2. freie Platte prüfen;
3. lokale, nicht committete Änderungen sichern;
4. Release-/Migrationshinweise lesen;
5. nachher Backend, nginx, Module und wichtige Integrationen prüfen.

### Backup

Mindestens sichern:

- `HH_DATA_DIR` (standardmäßig `/var/lib/hydrahive2`);
- `/etc/hydrahive2`;
- Projekt-Workspaces und externe Mounts, falls sie außerhalb liegen;
- externe Datenbanken und Extension-Daten separat.

Ein Backup der HydraHive-Dateien enthält nicht automatisch Daten von Docker-Volumes, entfernten Servern, Mailservern, Home Assistant oder anderen Drittanwendungen.

### Migration

Der Migrationsworkflow kann einen Server per rsync klonen. Bei großen Datenbeständen dauert das lange. Prüfe Quell-/Zielpfade, Kapazität, SSH-Verbindung und Servicezustand, bevor du startest.

---

## 15. Datenschutz und sensible Daten

### Cloud-Grenze

„Self-hosted“ bedeutet nicht automatisch „alles bleibt lokal“. Folgende Aktionen können Daten an Dritte senden:

- Cloud-LLM- oder Media-Provider;
- Websuche und Browserzugriffe;
- E-Mail, Messenger und Git-Hosting;
- Home Assistant oder andere externe APIs;
- externe MCP-Server.

Wähle für vertrauliche Aufgaben ein geeignetes lokales Modell oder einen ausdrücklich genehmigten Anbieter.

### Medizinische Daten

Patientenakte, FHIR und Health-Daten sind besonders sensibel. Gewähre nur notwendigen Benutzern und Agenten Zugriff, sichere Backups verschlüsselt und sende medizinische Inhalte nicht ungeprüft an Cloud-Modelle. HydraHive stellt keine Diagnose.

### Finanz- und Kryptodaten

Portfolio- und Finanzfunktionen sind Dokumentation/Auswertung, keine Anlage-, Steuer- oder Rechtsberatung. Prüfe Kurse, Buchungen und FIFO-Berechnungen gegen deine Originalunterlagen.

---

## 16. Häufige Probleme

### Die Seite lädt nicht

```bash
sudo systemctl status hydrahive2
sudo systemctl status nginx
sudo journalctl -u hydrahive2 -n 100 --no-pager
```

Prüfe außerdem Server-IP, Firewall, Zertifikatswarnung und freien Speicher.

### Ein Modell antwortet nicht

- Providerstatus und Credential prüfen;
- Modell im Katalog aktualisieren;
- Kontext-/Tokenlimit prüfen;
- testweise ein anderes erlaubtes Modell wählen;
- Fehleransicht und Backendlog prüfen;
- bei lokalem Modell Laufzeit und verfügbaren RAM/VRAM prüfen.

### Ein Tool fehlt

- ist es dem Agenten zugewiesen?
- ist das Modul/Plugin aktiviert?
- läuft der MCP-Server?
- hat der Benutzer die nötige Projekt-/Admin-Berechtigung?
- ist der externe Dienst erreichbar?

### Ein Lauf scheint festzuhängen

Öffne die Laufansicht und prüfe, ob:

- eine Tool-Bestätigung wartet;
- ein externer Dienst noch arbeitet;
- der Lauf abgekoppelt weiterläuft;
- das Iterationslimit erreicht wurde;
- ein Fehlerereignis vorliegt.

Nutze **Stoppen** nur, wenn die laufende Operation sicher abgebrochen werden kann.

### Ein Modul startet nicht

- Installationsjob und Backendlog prüfen;
- `manifest.json`, Mindest-Core-Version und Abhängigkeiten prüfen;
- Frontend neu laden;
- Backend nach einer Moduländerung neu starten;
- bei einem Drittmodul dessen Quelle/Version dokumentieren.

### API-Dokumentation

API-Dokumentation ist standardmäßig deaktiviert. Mit `HH_ENABLE_DOCS=true` liegt Swagger unter `/api/docs` und OpenAPI unter `/api/openapi.json`. Im Standard-Linux-Setup proxyt nginx `/api/` zum Loopback-Backend; veröffentliche die Dokumentation nur bewusst.

---

## 17. Hilfe und Fehlerberichte

Bei einem Fehlerbericht sind folgende Angaben hilfreich:

- HydraHive-Version oder Commit;
- Betriebssystem und Installationsart;
- betroffener Benutzer-/Projektbereich ohne Geheimnisse;
- genaue Schritte zur Reproduktion;
- erwartetes und tatsächliches Verhalten;
- relevante Browserkonsole und Serverlogs;
- Provider/Modell oder externe Integration;
- Zeitpunkt und Zeitzone.

API-Keys, Passwörter, Tokens, private Schlüssel, Patientendaten und vollständige vertrauliche Prompts vor dem Teilen entfernen.
