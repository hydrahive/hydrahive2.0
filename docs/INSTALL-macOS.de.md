# HydraHive auf dem Mac installieren – Schritt für Schritt

> **Status: experimentell.** HydraHive läuft auf dem Mac (getestet zuletzt am 01.10.2026 auf einem Intel-iMac mit
> macOS 15). Der Mac-Installer ist aber einfacher als der Linux-Installer: Einige Funktionen gibt es auf dem Mac
> nicht (siehe [Was auf dem Mac nicht geht](#was-auf-dem-mac-nicht-geht)). Für einen Server, der rund um die Uhr
> läuft, empfehlen wir Linux (Ubuntu).

English version: [INSTALL-macOS.md](INSTALL-macOS.md)

---

## Auf einen Blick

| | |
|---|---|
| **Dauer** | ca. 20–40 Minuten (der größte Teil ist Download) |
| **Schwierigkeit** | Du tippst ein paar Befehle ins **Terminal**. Jeder Befehl steht unten zum Kopieren. |
| **Danach** | HydraHive läuft im Hintergrund und startet beim Hochfahren des Macs automatisch. Du öffnest es im Browser. |

---

## 1. Was du brauchst

| | Mindestens | Empfohlen |
|---|---|---|
| **Mac** | Intel oder Apple Silicon (M1–M5) | Apple Silicon |
| **macOS** | 13 (Ventura) | 15 (Sequoia) oder neuer |
| **Arbeitsspeicher** | 8 GB | 16 GB oder mehr (mit lokalen KI-Modellen: 32 GB+) |
| **Freier Speicher** | 10 GB | 30 GB+ (Datenbank, Medien, lokale Modelle) |
| **Benutzerkonto** | ein Konto mit **Administratorrechten** (du musst dein Mac-Passwort für `sudo` eingeben können) | |
| **Internet** | während der Installation | |

> **Hinweis zu macOS-Versionen:** Homebrew (siehe Schritt 3) unterstützt offiziell macOS 15 und neuer auf Apple
> Silicon. Ältere Versionen und Intel-Macs laufen bei Homebrew als „nicht offiziell unterstützt“, funktionieren aber
> meist. Getestet haben wir HydraHive bisher auf einem **Intel-iMac mit macOS 15.3**.

**Außerdem brauchst du für die KI selbst** (das kommt nach der Installation, Schritt 9) eines davon:
- einen **API-Schlüssel** eines KI-Anbieters (z. B. Anthropic, OpenAI, OpenRouter) **oder** ein Login per ChatGPT/Claude-Abo, **oder**
- **Ollama** für lokale Modelle direkt auf dem Mac (kostenlos, braucht aber viel Arbeitsspeicher).

---

## 2. Terminal öffnen

1. Drücke **⌘ + Leertaste** (Spotlight).
2. Tippe **Terminal** und drücke **Enter**.

Ein Fenster mit Text öffnet sich. Hier fügst du die Befehle ein: kopieren, ins Terminal klicken, **⌘ + V**, **Enter**.

> **Passwort-Eingabe:** Wenn das Terminal `Password:` anzeigt, tippst du dein **Mac-Passwort**. Beim Tippen erscheinen
> **keine Zeichen** – das ist normal. Einfach tippen und Enter drücken.

---

## 3. Entwickler-Werkzeuge und Homebrew installieren

**Homebrew** ist ein Programm, das andere Programme installiert (Python, Node.js, Datenbank …). Der HydraHive-Installer
braucht es.

**3a. Apple-Entwickler-Werkzeuge** (falls noch nicht vorhanden):

```bash
xcode-select --install
```

Es öffnet sich ein Fenster → **Installieren** klicken und warten (ein paar Minuten).
Kommt die Meldung „already installed“, ist alles schon da – weiter mit 3b.

**3b. Homebrew installieren** (Befehl von [brew.sh](https://brew.sh)):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Der Installer fragt nach deinem Passwort und zeigt an, was er tun wird – mit **Enter** bestätigen.

**3c. Wichtig – Homebrew dauerhaft einrichten.** Am Ende zeigt Homebrew unter **„Next steps“** zwei Befehle an.
**Genau diese** ausführen. Sie sehen so aus:

- **Apple Silicon (M1–M5):**
  ```bash
  echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  eval "$(/opt/homebrew/bin/brew shellenv)"
  ```
- **Intel-Mac:**
  ```bash
  echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
  eval "$(/usr/local/bin/brew shellenv)"
  ```

**Prüfen:**

```bash
brew --version
```

Es erscheint eine Versionsnummer (z. B. `Homebrew 4.x.x`)? → Weiter.
`command not found`? → Schritt 3c nochmal, dann das Terminal schließen und neu öffnen.

---

## 4. HydraHive herunterladen

HydraHive kommt nach **`/opt/hydrahive2`** (dort sucht der Installer).

```bash
brew install git
sudo mkdir -p /opt/hydrahive2
sudo chown "$(whoami)" /opt/hydrahive2
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2
cd /opt/hydrahive2
```

> Du willst einen anderen Ordner? Dann vor dem Installer `export HH_REPO_DIR=/dein/pfad` setzen. Für Anfänger:
> einfach `/opt/hydrahive2` lassen.

---

## 5. Installer starten

```bash
cd /opt/hydrahive2
bash installer/install-mac.sh
```

**Wichtig:** **Nicht** mit `sudo` starten. Der Installer fragt selbst nach deinem Passwort, wenn er es braucht.

### Was der Installer macht (dauert 10–30 Minuten)

| Phase | Was passiert |
|---|---|
| 1 | Installiert per Homebrew: Python 3.12, Node.js, git, ffmpeg, GitHub-CLI, außerdem `uv` und `mmx-cli` |
| 2 | Legt die Ordner an: Daten unter `/usr/local/var/hydrahive2`, Einstellungen unter `/usr/local/etc/hydrahive2` |
| 3 | Richtet das Backend ein (Python-Umgebung) |
| 4 | Baut die Web-Oberfläche (dauert am längsten) |
| 5 | Installiert die Datenbank PostgreSQL 16 mit pgvector (für Datamining/Gedächtnis) |
| 6 | Richtet HydraHive als **Hintergrund-Dienst** ein (startet automatisch beim Hochfahren) |
| 7 | Richtet den Webserver **nginx** mit HTTPS ein (selbst erstelltes Zertifikat) |

Am Ende erscheint ein grüner Kasten:

```
HydraHive2 — Installation fertig (Mac)
  URL:       https://192.168.x.x
  Benutzer:  admin
  Passwort:  <zufälliges Passwort>
```

> ### ⚠️ Das Passwort sofort notieren!
> Es wird **nur einmal** angezeigt. Wenn statt des Passworts `(siehe: log show --process uvicorn)` erscheint, siehe
> [Problemlösung → Admin-Passwort](#admin-passwort-nicht-angezeigt).

---

## 6. HydraHive im Browser öffnen

- **Auf demselben Mac:** <https://localhost>
- **Von einem anderen Gerät im Heimnetz** (Handy, Laptop): die **URL aus dem grünen Kasten**, z. B. `https://192.168.1.50`

### Die Sicherheitswarnung ist normal
HydraHive erstellt sich ein eigenes Zertifikat. Der Browser kennt es nicht und warnt deshalb:

- **Safari:** „Details einblenden“ → „diese Website besuchen“ → bestätigen
- **Chrome:** „Erweitert“ → „Weiter zu … (unsicher)“
- **Firefox:** „Erweitert…“ → „Risiko akzeptieren und fortfahren“

Das ist nur beim ersten Mal nötig.

---

## 7. Anmelden und Passwort ändern

1. Anmelden mit **admin** und dem Passwort aus Schritt 5.
2. **Sofort ein eigenes Passwort setzen** (über dein Profil bzw. die Benutzerverwaltung).

---

## 8. Prüfen, ob alles läuft

```bash
sudo launchctl list | grep io.hydrahive
```

Du solltest Einträge für **`io.hydrahive.backend`** und **`io.hydrahive.nginx`** sehen.

```bash
curl -sk https://localhost/api/health
```

Erwartet: eine Zeile mit `"status":"ok"`.

---

## 9. KI einrichten (sonst antwortet Buddy nicht)

Nach der Installation ist **noch kein KI-Modell** eingerichtet. Im Cockpit:

**Einstellungen → KI-Modelle**, dann eine der Möglichkeiten:

| Möglichkeit | Für wen | Hinweis |
|---|---|---|
| **API-Schlüssel** (Anthropic, OpenAI, OpenRouter, NVIDIA …) | schnellster Start | kostet je nach Nutzung |
| **Login mit ChatGPT- oder Claude-Abo** | wer schon ein Abo hat | |
| **Ollama (lokal)** | Datenschutz, offline | braucht viel RAM; Anleitung unten |

> Wenn nach einem Login neue Modelle nicht in der Auswahl erscheinen: einmal den Dienst neu starten (siehe
> [Nützliche Befehle](#nützliche-befehle)).

### Optional: lokale Modelle mit Ollama
1. Ollama installieren: `brew install ollama` (oder die App von [ollama.com](https://ollama.com))
2. Starten: `brew services start ollama`
3. Ein Modell laden, z. B.: `ollama pull qwen3:8b` (Modellgröße passend zum Arbeitsspeicher wählen)
4. In HydraHive unter **Einstellungen → KI-Modelle** einen Ollama-Anbieter mit der Adresse
   `http://localhost:11434` anlegen.

Details: [docs/ollama-provider.md](ollama-provider.md)

---

## Was auf dem Mac nicht geht

Der Mac-Installer richtet nur den **Kern** ein. Folgendes gibt es auf dem Mac **nicht** (oder nur von Hand):

| Funktion | Auf dem Mac | Warum |
|---|---|---|
| **VMs & Container** (libvirt/QEMU, Incus) | ❌ nicht verfügbar | gibt es nur unter Linux |
| **Voice / Spracherkennung als Dienst** (Whisper-Container) | ❌ nicht automatisch | läuft unter Linux in einem Incus-Container |
| **WhatsApp-Anbindung** | ❌ nicht eingerichtet | Bridge wird nur vom Linux-Installer aufgesetzt |
| **Samba-Freigaben** (Projektordner im Netzwerk) | ❌ nicht verfügbar | Linux-Modul |
| **Tailscale-Fernzugriff** | ⚠️ nicht automatisch | Tailscale-App für macOS selbst installieren |
| **Websuche (SearXNG)** | ⚠️ nicht automatisch | eigene SearXNG-Adresse unter Einstellungen eintragen, sonst funktioniert das Werkzeug `web_search` nicht |
| **Start-Agenten & MCP-Server** | ⚠️ nicht automatisch | Linux legt sie beim Installieren an; auf dem Mac von Hand im Cockpit anlegen |
| **Lokale Medien-Modelle** (Bild/Video mit NVIDIA-GPU) | ❌ nicht verfügbar | braucht NVIDIA + Docker |
| **Erweiterungen** (Einstellungen → Erweiterungen) | ⚠️ meist nicht | viele brauchen `apt`/`docker` und brechen mit einer unklaren Fehlermeldung ab |
| **Module** (Einstellungen → Module) | ✅ fast alle | getestet 21 von 22; **OpenTor** geht nicht (Tor nur über Linux-Pakete) |
| **Firewall-Regeln** (ufw) | ❌ | macOS nutzt eine eigene Firewall |

**Was gut geht:** Cockpit, Buddy, Agenten, Projekte, Werkstatt, Datamining/Gedächtnis, Aufgaben, Module wie Atelier,
Storyteller, Haushaltsbuch usw., Updates über das Cockpit.

---

## Worauf du achten musst

- **Der Mac muss wach bleiben.** HydraHive läuft nur, solange der Mac eingeschaltet ist und **nicht schläft**.
  Für Dauerbetrieb: **Systemeinstellungen → Energie** (bzw. „Batterie“ → „Optionen“) → Ruhezustand verhindern,
  Laptop am Netzteil lassen.
- **Ports 80 und 443** werden von HydraHive (nginx) belegt. Läuft auf dem Mac schon ein anderer Webserver, gibt es
  einen Konflikt.
- **Zugriff aus dem Netz:** Andere Geräte erreichen HydraHive über die IP-Adresse des Macs. Wechselt die Adresse (z. B.
  anderes WLAN), passt das Zertifikat nicht mehr ganz – die Browser-Warnung kommt dann wieder.
- **macOS-Firewall:** Ist sie an, fragt macOS beim ersten Start, ob nginx Verbindungen annehmen darf → **Erlauben**.
- **Nicht `sudo bash installer/install-mac.sh`** – immer als normaler Benutzer starten.
- **Backups:** Deine Daten liegen unter `/usr/local/var/hydrahive2`, die Einstellungen (inkl. Schlüssel) unter
  `/usr/local/etc/hydrahive2`. Diese beiden Ordner sichern. Time Machine sichert sie mit.

---

## Nützliche Befehle

| Was | Befehl |
|---|---|
| Dienst neu starten | `sudo launchctl kickstart -k system/io.hydrahive.backend` |
| Läuft der Dienst? | `sudo launchctl list \| grep io.hydrahive` |
| Fehler-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-error.log` |
| Update-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-update.log` |
| Webserver-Fehler | `tail -50 /usr/local/var/log/nginx-hydrahive-error.log` |

### Updates
Am einfachsten im Cockpit über die Update-Funktion. Von Hand:

```bash
eval "$(brew shellenv)"
bash /opt/hydrahive2/installer/update-mac.sh
```

---

## Problemlösung

### `brew: command not found`
Homebrew ist nicht im Pfad → Schritt 3c ausführen, Terminal schließen und neu öffnen.

### `node`, `npm` oder `python3.12` „command not found“ beim Update
Gleiche Ursache. Vor dem Update `eval "$(brew shellenv)"` ausführen (steht im Update-Befehl oben schon drin).

### Admin-Passwort nicht angezeigt
Das Passwort steht beim ersten Start einmal im Log und in einer Datei:

```bash
sudo cat /usr/local/etc/hydrahive2/.admin_initial_password
```

Gibt es die Datei nicht mehr, im System-Log suchen:

```bash
log show --predicate 'process == "uvicorn"' --last 1h | grep "Passwort:"
```

### Installer bricht bei `npm install` ab („network“, „ECONNRESET“)
Meist ein kurzer Netzwerk-Aussetzer beim Download. Einfach den Installer **nochmal starten** – er macht dort weiter,
wo er war (fertige Schritte werden übersprungen).

### Update meldet „git pull fehlgeschlagen“
Das passiert, wenn sich die Versionsgeschichte auf GitHub geändert hat. Lösung (verwirft **nur** lokale Änderungen am
Programmcode, nicht deine Daten):

```bash
cd /opt/hydrahive2
git fetch origin
git reset --hard origin/main
bash installer/update-mac.sh
```

### Browser zeigt nach einem Update noch die alte Oberfläche
Browser-Cache. Seite mit **⌘ + Shift + R** neu laden.

### Seite lädt gar nicht
1. Läuft der Dienst? → `sudo launchctl list | grep io.hydrahive`
2. Fehler-Log ansehen → `tail -50 /usr/local/var/log/hydrahive2-error.log`
3. Dienst neu starten → `sudo launchctl kickstart -k system/io.hydrahive.backend`

Kommst du nicht weiter? Frag im **#⚠️supportforum** auf unserem Discord: <https://discord.gg/GVCZvNxxFA> –
am besten mit den letzten Zeilen aus dem Fehler-Log (vorher Passwörter/Schlüssel darin unkenntlich machen).
