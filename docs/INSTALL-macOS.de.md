# HydraHive auf dem Mac installieren – Schritt für Schritt

> **Status: experimentell.** HydraHive läuft auf dem Mac, der Mac-Installer ist aber einfacher als der
> Linux-Installer. Einige Funktionen gibt es auf dem Mac nicht (siehe [Was auf dem Mac nicht geht](#was-auf-dem-mac-nicht-geht)).
> Für einen Server, der rund um die Uhr läuft, empfehlen wir Linux (Ubuntu).
> Zuletzt getestet: 01.10.2026 auf einem Intel-iMac mit macOS 15.3.

English version: [INSTALL-macOS.md](INSTALL-macOS.md) ·
Du lässt eine KI installieren? → [Kurzfassung für KI-Assistenten](#kurzfassung-für-ki-assistenten)

---

## Inhalt

0. [Bevor du anfängst – die wichtigsten Fragen](#0-bevor-du-anfängst--die-wichtigsten-fragen)
1. [Prüfen: Welchen Mac habe ich?](#1-prüfen-welchen-mac-habe-ich)
2. [Am Mac anmelden – mit dem richtigen Benutzer](#2-am-mac-anmelden--mit-dem-richtigen-benutzer)
3. [Das Terminal finden und bedienen](#3-das-terminal-finden-und-bedienen)
4. [Homebrew installieren](#4-homebrew-installieren)
5. [HydraHive herunterladen](#5-hydrahive-herunterladen)
6. [Installer starten – und was dann passiert](#6-installer-starten--und-was-dann-passiert)
7. [Im Browser öffnen und anmelden](#7-im-browser-öffnen-und-anmelden)
8. [KI einrichten (sonst antwortet Buddy nicht)](#8-ki-einrichten-sonst-antwortet-buddy-nicht)
9. [Prüfen, ob alles läuft](#9-prüfen-ob-alles-läuft)
- [Was auf dem Mac nicht geht](#was-auf-dem-mac-nicht-geht) · [Worauf du achten musst](#worauf-du-achten-musst) ·
  [Nützliche Befehle](#nützliche-befehle) · [Problemlösung](#problemlösung) · [Deinstallieren](#deinstallieren) ·
  [Kurzfassung für KI-Assistenten](#kurzfassung-für-ki-assistenten)

---

## 0. Bevor du anfängst – die wichtigsten Fragen

| Frage | Antwort |
|---|---|
| **Wie lange dauert das?** | 30–60 Minuten. Das meiste ist Warten auf Downloads. |
| **Muss ich programmieren können?** | Nein. Du kopierst Befehle aus dieser Anleitung in das Programm **Terminal**. Jeder Befehl steht hier zum Kopieren. |
| **Brauche ich einen speziellen Benutzer?** | **Nein, aber einen Administrator.** Du nimmst dein normales Mac-Benutzerkonto, wenn es Administratorrechte hat. HydraHive läuft danach unter **genau diesem Benutzer**. Lösche ihn später also nicht. Ein eigenes Konto nur für HydraHive ist möglich, aber nicht nötig (siehe [Schritt 2](#2-am-mac-anmelden--mit-dem-richtigen-benutzer)). |
| **Welches Passwort wird abgefragt?** | Immer **das Passwort, mit dem du dich am Mac anmeldest**. Erst ganz am Ende bekommst du ein neues, zufälliges Passwort für HydraHive. |
| **Brauche ich Internet?** | Ja, während der ganzen Installation. |
| **Kostet das etwas?** | HydraHive und alle Programme, die installiert werden, sind kostenlos. Für die KI selbst brauchst du **danach** entweder einen Zugang bei einem KI-Anbieter (kostet je nach Nutzung) oder ein lokales Modell über Ollama (kostenlos, braucht viel Arbeitsspeicher). |
| **Was, wenn etwas schiefgeht?** | Den Installer einfach nochmal starten. Was schon installiert ist, wird übersprungen. Und es gibt die [Problemlösung](#problemlösung) und unser [Discord](https://discord.gg/GVCZvNxxFA). |

**Das brauchst du:**

| | Mindestens | Empfohlen |
|---|---|---|
| **Mac** | Apple Silicon (M1 oder neuer). Intel geht nur eingeschränkt, siehe [Schritt 1](#1-prüfen-welchen-mac-habe-ich) | Apple Silicon |
| **macOS** | 13 (Ventura); 13–14 gilt bei Homebrew als „nicht offiziell unterstützt“, läuft aber meist | 15 (Sequoia) oder neuer |
| **Arbeitsspeicher** | 8 GB | 16 GB oder mehr (mit lokalen KI-Modellen: 32 GB+) |
| **Freier Speicher** | 15 GB | 30 GB+ |
| **Benutzerkonto** | eines mit **Administratorrechten** | |

---

## 1. Prüfen: Welchen Mac habe ich?

1. Klicke oben links auf das **Apfel-Symbol **.
2. Wähle **„Über diesen Mac“**.
3. Schau auf die Zeile **„Chip“** bzw. **„Prozessor“** und auf die Zeile **„macOS“**.

| Dort steht … | Bedeutung |
|---|---|
| **Chip: Apple M1 / M2 / M3 / M4 …** | ✅ Apple Silicon. Diese Anleitung passt genau. |
| **Prozessor: … Intel Core …** | ⚠️ Intel-Mac. Lies den Kasten unten, **bevor** du weitermachst. |
| **macOS 12 oder älter** | ❌ zu alt. Erst macOS aktualisieren (Systemeinstellungen → Allgemein → Softwareupdate). |

> ### ⚠️ Intel-Macs: Stand Oktober 2026
> Homebrew ist das Programm, das HydraHive für die Installation braucht. Es hat die Unterstützung für Intel-Macs
> im September 2026 stark eingeschränkt:
> - Das **offizielle Installationsskript** von brew.sh bricht auf Intel mit der Meldung
>   `Homebrew on macOS is only supported on Apple Silicon processors!` ab.
> - Homebrew baut **keine neuen Fertigpakete** mehr für Intel. Manche Programme werden dann auf deinem Mac aus dem
>   Quellcode gebaut. Das kann **Stunden** dauern.
> - Ab September 2027 soll Homebrew auf Intel gar nicht mehr laufen.
>
> **Ist Homebrew auf deinem Intel-Mac schon installiert?** Tippe im Terminal (siehe Schritt 3) `brew --version`.
> Erscheint eine Versionsnummer, kannst du Schritt 4 überspringen. So lief auch unser Test im Oktober 2026.
>
> **Ist Homebrew noch nicht installiert?** Dann ist der Mac-Weg für dich mühsam. Wir empfehlen:
> HydraHive auf einem Linux-Rechner installieren oder einen Mac mit Apple Silicon nehmen. Einen Notweg findest du
> in [Problemlösung → Intel-Mac ohne Homebrew](#intel-mac-ohne-homebrew). Den haben wir nicht getestet.

---

## 2. Am Mac anmelden – mit dem richtigen Benutzer

Du meldest dich **ganz normal am Mac an**, so wie jeden Tag am Anmeldebildschirm mit deinem Namen und Passwort.
Wichtig ist nur: Das Konto muss **Administratorrechte** haben.

**So prüfst du das:**

1. **Apfel-Symbol ** → **Systemeinstellungen**.
2. Links in der Liste **„Benutzer:innen & Gruppen“** anklicken.
3. Unter deinem Namen steht **„Admin“**? → ✅ Passt.
   Steht dort „Standard“? → Du brauchst ein anderes Konto. Melde dich mit einem Konto an, unter dem „Admin“ steht,
   oder lass dir von der Person, der der Mac gehört, Administratorrechte geben.

**Merke dir den Kurznamen deines Kontos.** Den brauchst du später nicht unbedingt, er hilft aber bei Problemen.
Du findest ihn im Terminal mit dem Befehl `whoami`.

> **Soll HydraHive unter einem eigenen Konto laufen?** Das geht. Lege unter „Benutzer:innen & Gruppen“ ein neues
> Konto vom Typ **Administrator** an (z. B. „hydrahive“), melde dich ab, melde dich mit dem neuen Konto an und
> mach dort ab Schritt 3 weiter. Für den Anfang ist das aber **nicht nötig**.

> **Der Mac steht woanders? Fernanmeldung per SSH.** Am Mac: **Systemeinstellungen → Allgemein → Teilen →
> „Entfernte Anmeldung“** einschalten. Dann von einem anderen Computer aus im Terminal
> `ssh deinkurzname@IP-des-Macs` eingeben. Die IP-Adresse steht unter **Systemeinstellungen → WLAN** bzw.
> **Netzwerk → Details**. Alle weiteren Befehle funktionieren genauso. Einzige Ausnahme: Das Fenster in Schritt 4a
> erscheint auf dem Bildschirm des Macs.

---

## 3. Das Terminal finden und bedienen

Das **Terminal** ist ein Programm, das bei jedem Mac dabei ist. Dort tippst bzw. fügst du die Befehle ein.

### Terminal öffnen – zwei Wege

**Weg A: Spotlight (am schnellsten)**
1. Drücke gleichzeitig **⌘ (Command) + Leertaste**. In der Mitte des Bildschirms erscheint ein Suchfeld.
2. Tippe `Terminal`.
3. Drücke **Enter**.

**Weg B: über den Finder**
1. Klicke im Dock (die Leiste unten) auf den **Finder** (das blau-weiße Gesicht).
2. Links auf **„Programme“** klicken.
3. Den Ordner **„Dienstprogramme“** öffnen.
4. Doppelklick auf **„Terminal“**.

### So sieht das Terminal aus

Ein Fenster mit einer Zeile wie dieser:

```
anna@Annas-MacBook ~ %
```

Das ist die **Eingabezeile**. Das `%` am Ende heißt: „Ich warte auf einen Befehl.“

### Einen Befehl ausführen

1. Hier in der Anleitung den Befehl **kopieren**. Auf GitHub gibt es rechts oben an jedem grauen Kasten ein
   **Kopier-Symbol** (zwei Rechtecke). Oder den Text markieren und **⌘ + C** drücken.
2. Ins Terminal-Fenster klicken.
3. **⌘ + V** drücken (Einfügen).
4. **Enter** drücken.
5. **Warten**, bis wieder die Eingabezeile mit `%` erscheint. Erst dann ist der Befehl fertig.

> **Passwort-Abfrage:** Zeigt das Terminal `Password:`, tippst du **dein Mac-Anmeldepasswort** und drückst
> **Enter**. **Beim Tippen erscheint nichts**, keine Punkte und keine Sternchen. Das ist normal, das Passwort wird
> trotzdem eingegeben. Steht danach `Sorry, try again`, war es falsch getippt. Einfach nochmal versuchen.

> **Ein Befehl hängt oder du willst abbrechen?** **Ctrl + C** drücken (die Taste „control“, nicht ⌘).

---

## 4. Homebrew installieren

**Homebrew** ist ein Programm, das andere Programme installiert (Python, Node.js, die Datenbank …).
Der HydraHive-Installer braucht es.

**Schon installiert?** Prüfe das zuerst:

```bash
brew --version
```

- Erscheint `Homebrew 4.x.x` oder höher? → **Weiter mit Schritt 5.**
- Erscheint `zsh: command not found: brew`? → Weiter mit 4a.

### 4a. Apple-Entwicklerwerkzeuge

```bash
xcode-select --install
```

- Es öffnet sich ein **Fenster** → auf **„Installieren“** klicken → Lizenz **„Akzeptieren“** → warten (5–15 Minuten).
- Kommt stattdessen `… Command line tools are already installed …`? → Schon da, weiter mit 4b.

### 4b. Homebrew selbst

Der Befehl stammt von der offiziellen Seite [brew.sh](https://brew.sh):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Was dann passiert:
1. Erscheint `Password:` → **Mac-Passwort** tippen, Enter.
2. Eine Liste, was installiert wird, und dann
   `Press RETURN/ENTER to continue or any other key to abort:` → **Enter** drücken.
3. Warten (5–15 Minuten). Am Ende steht **`==> Installation successful!`**.

### 4c. Homebrew dauerhaft einrichten (wichtig!)

Ganz unten zeigt Homebrew den Abschnitt **`==> Next steps:`** mit **ein bis drei Befehlen**. **Genau diese**
der Reihe nach kopieren und ausführen. Auf einem Apple-Silicon-Mac sehen sie so aus:

```bash
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv zsh)"
```

Zeigt Homebrew keine solchen Befehle an, ist nichts zu tun.

**Prüfen:** Terminal ganz schließen (**⌘ + Q**), neu öffnen (Schritt 3) und eingeben:

```bash
brew --version
```

✅ `Homebrew 4.x.x` oder höher → weiter.
❌ `command not found` → 4c nochmal genau mit den Befehlen aus **deinem** Terminal-Fenster ausführen.

---

## 5. HydraHive herunterladen

HydraHive kommt in den Ordner **`/opt/hydrahive2`**. Dort sucht der Installer danach.
Diese fünf Befehle **einzeln nacheinander** ausführen:

```bash
brew install git
```
```bash
sudo mkdir -p /opt/hydrahive2
```
→ fragt nach deinem Mac-Passwort.
```bash
sudo chown "$(whoami)" /opt/hydrahive2
```
```bash
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2
```
→ lädt HydraHive herunter. Am Ende steht `Resolving deltas: 100% … done.`
```bash
cd /opt/hydrahive2
```

**Prüfen:**

```bash
ls /opt/hydrahive2/installer/install-mac.sh
```

✅ Es erscheint `/opt/hydrahive2/installer/install-mac.sh` → weiter.
❌ `No such file or directory` → der `git clone` hat nicht geklappt. Lies die Fehlermeldung darüber.
Steht dort `already exists and is not an empty directory`, liegt dort schon etwas. Dann siehe
[Problemlösung](#ordner-opthydrahive2-existiert-schon).

---

## 6. Installer starten – und was dann passiert

```bash
cd /opt/hydrahive2
bash installer/install-mac.sh
```

> ⚠️ **Nicht** `sudo bash …` eingeben! Der Installer läuft als **dein** Benutzer und fragt selbst nach dem Passwort,
> wenn er es braucht. Mit `sudo` würde HydraHive dem Systemkonto „root“ gehören und später nicht richtig laufen.

### Was du im Terminal siehst

Der Installer arbeitet in Phasen. Jede beginnt mit einer türkisen Zeile `[hh2-mac] Phase …`:

| Phase | Was passiert | Dauer (ca.) | Musst du etwas tun? |
|---|---|---|---|
| **1** System-Dependencies | Installiert Python 3.12, Node.js, git, ffmpeg, GitHub-CLI, `uv` und `mmx-cli` | 5–20 min | nein |
| **2** Verzeichnisse | Legt Ordner für Daten und Einstellungen an | Sekunden | **ja: `Password:` → Mac-Passwort** |
| **3** Python-venv + Backend | Richtet das Programm im Hintergrund ein | 2–5 min | nein |
| **4** Frontend | Baut die Weboberfläche | 3–10 min | nein |
| **5** PostgreSQL | Installiert die Datenbank für Gedächtnis und Suche | 2–5 min | nein |
| **6 / 6b** launchd-Service | Richtet HydraHive als Hintergrund-Dienst ein, der beim Hochfahren startet | Sekunden | **evtl. nochmal `Password:`** (auch in Phase 7 möglich) |
| **7** nginx | Richtet den Webserver mit HTTPS ein | 1–2 min | nein |

**Bleib in der Nähe.** macOS merkt sich dein Passwort nur 5 Minuten. Dauern die Phasen 3–5 länger, fragt der
Installer in Phase 6 noch einmal. Bis du es eingibst, wartet er einfach.

Zwischendurch erscheinen viele Zeilen wie `· brew install python@3.12` oder `· npm install`. Gelbe Warnungen
(`npm warn …`, `Warning: …`) sind meist harmlos. **Rote Meldungen, nach denen der Installer stoppt**, sind echte
Fehler, siehe [Problemlösung](#problemlösung).

### Das Ende: der grüne Kasten

Zuletzt steht dort `Warte auf den ersten Start (Admin-Passwort) …`. Das dauert bis zu einer Minute. Dann erscheint:

```
╔══════════════════════════════════════════════╗
║     HydraHive2 — Installation fertig (Mac)   ║
╠══════════════════════════════════════════════╣
║  URL:       https://192.168.1.50             ║
║  Benutzer:  admin                            ║
║  Passwort:  Xy7_kQ2mP9vLr4Tz                 ║
╠══════════════════════════════════════════════╣
```

> ### ⚠️ Das Passwort sofort notieren!
> Das ist dein **HydraHive-Passwort** für den Benutzer `admin`. Es ist **nicht** dein Mac-Passwort und wird **nur
> dieses eine Mal** angezeigt. Schreib es auf oder speichere es in deinem Passwort-Manager.
>
> Steht dort `(nicht neu – siehe Anleitung)`, siehe
> [Problemlösung → Admin-Passwort fehlt](#admin-passwort-fehlt).

**Die Installation ist fertig.** Du kannst das Terminal offen lassen oder schließen. HydraHive läuft im Hintergrund
weiter und startet bei jedem Hochfahren des Macs von selbst.

---

## 7. Im Browser öffnen und anmelden

1. Öffne einen Browser (Safari, Chrome oder Firefox).
2. Gib in die Adresszeile ein:
   - **Auf demselben Mac:** `https://localhost`
   - **Von einem anderen Gerät im selben WLAN** (Handy, Laptop): die **URL aus dem grünen Kasten**, z. B.
     `https://192.168.1.50`

### Die Sicherheitswarnung ist normal

HydraHive hat sich ein eigenes Zertifikat ausgestellt. Der Browser kennt es nicht und warnt deshalb. Die Verbindung
ist trotzdem verschlüsselt.

- **Safari:** „Details einblenden“ → „diese Website besuchen“ → nochmal „Website besuchen“ (evtl. fragt Safari nach dem Mac-Passwort)
- **Chrome:** „Erweitert“ → „Weiter zu … (unsicher)“
- **Firefox:** „Erweitert…“ → „Risiko akzeptieren und fortfahren“

### Anmelden

1. **Benutzername:** `admin`
2. **Passwort:** das Passwort aus dem grünen Kasten
3. **Sofort ein eigenes Passwort setzen:** Öffne `https://localhost/profile`. Alternativ klickst du oben bzw.
   unten auf den **Kreis mit deinem Anfangsbuchstaben** → **Profil**. Dann **„Passwort ändern“**: aktuelles
   Passwort eintragen, neues Passwort (mindestens 8 Zeichen) eintragen, speichern.

---

## 8. KI einrichten (sonst antwortet Buddy nicht)

Nach der Installation ist **noch kein KI-Modell** eingerichtet. Ohne Modell antwortet Buddy nicht.

1. Öffne `https://localhost/llm`. Alternativ: **Einstellungen → KI-Modelle**.
2. Klicke auf **„Provider hinzufügen“**.
3. Wähle einen Anbieter und trage den Zugang ein:

| Möglichkeit | Für wen | Was du brauchst |
|---|---|---|
| **API-Schlüssel** (Anthropic, OpenAI, OpenRouter, Mistral, Gemini, NVIDIA …) | schnellster Start | einen Schlüssel vom Anbieter (beginnt z. B. mit `sk-…`); kostet je nach Nutzung |
| **Anthropic per Login** oder **ChatGPT Plus/Pro (Codex)** | wer schon ein Abo hat | den Login-Knopf im Formular, kein Schlüssel nötig |
| **Ollama (lokal)** | Datenschutz, offline | viel Arbeitsspeicher; Anleitung unten |

4. Speichern. Danach unter **„Standard-Modelle“** ein Modell als Standard auswählen.
5. **Test:** `https://localhost/buddy` öffnen und „Hallo“ schreiben. Kommt eine Antwort? → 🎉 Fertig!

> Erscheinen nach einem Login keine Modelle in der Auswahl? Starte den Dienst einmal neu, siehe
> [Nützliche Befehle](#nützliche-befehle).

### Optional: lokale Modelle mit Ollama

```bash
brew install ollama
brew services start ollama
ollama pull qwen3:8b
```

`qwen3:8b` ist ein rund 5 GB großer Download. Mit 8 GB RAM nimmst du lieber ein kleineres Modell, z. B. `qwen3:4b`.
Danach in HydraHive unter **Provider hinzufügen** den Eintrag **„Ollama (lokal)“** wählen. Adresse:
`http://localhost:11434`. Details: [ollama-provider.md](ollama-provider.md)

---

## 9. Prüfen, ob alles läuft

```bash
sudo launchctl list | grep io.hydrahive
```

Erwartet sind vier Zeilen mit `io.hydrahive.backend`, `io.hydrahive.nginx`, `io.hydrahive.update` und
`io.hydrahive.restart`. Steht in der ersten Spalte eine **Zahl**, läuft der Dienst. Ein `-` ist bei
`update`/`restart` normal, die laufen nur bei Bedarf.

```bash
curl -sk https://localhost/api/health
```

Erwartet ist eine Zeile mit `"status":"ok"`.

```bash
brew services list | grep postgresql
```

Erwartet: `postgresql@16  started`.

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
| **Websuche (SearXNG)** | ⚠️ nicht automatisch | eigene SearXNG-Adresse in den Einstellungen eintragen, sonst funktioniert `web_search` nicht |
| **Start-Agenten & MCP-Server** | ⚠️ nicht automatisch | Linux legt sie beim Installieren an, auf dem Mac von Hand im Cockpit anlegen |
| **Lokale Medien-Modelle** (Bild/Video mit NVIDIA-GPU) | ❌ nicht verfügbar | braucht NVIDIA + Docker |
| **Erweiterungen** (Einstellungen → Erweiterungen) | ⚠️ meist nicht | viele brauchen `apt`/`docker` und brechen mit einer unklaren Fehlermeldung ab |
| **Module** (Einstellungen → Module) | ✅ fast alle | getestet: 21 von 22; **OpenTor** geht nicht (Tor nur über Linux-Pakete) |
| **Firewall-Regeln** (ufw) | ❌ | macOS nutzt eine eigene Firewall |

**Was gut geht:** Cockpit, Buddy, Agenten, Projekte, Werkstatt, Datamining/Gedächtnis, Aufgaben, Module wie Atelier,
Storyteller, Haushaltsbuch usw. und Updates über das Cockpit.

---

## Worauf du achten musst

- **Der Mac muss wach bleiben.** HydraHive läuft nur, solange der Mac an ist und **nicht schläft**. Für Dauerbetrieb:
  **Systemeinstellungen → Energie** (beim Laptop: **Batterie → Optionen**) → Ruhezustand bei ausgeschaltetem
  Display verhindern. Laptops am Netzteil lassen.
- **Nach einem Neustart des Macs einmal anmelden.** Die Datenbank (PostgreSQL) startet erst, wenn sich **der
  Benutzer, der installiert hat**, am Mac anmeldet. HydraHive selbst startet schon vorher, dann aber ohne
  Gedächtnis-Suche (Datamining). Deshalb: nach jedem Neustart mit diesem Benutzer anmelden und dann einmal
  `sudo launchctl kickstart -k system/io.hydrahive.backend` ausführen. Das ist eine bekannte Einschränkung des
  Mac-Installers.
- **Den Installations-Benutzer nicht löschen.** HydraHive läuft unter diesem Konto.
- **Ports 80 und 443** belegt HydraHive (nginx). Läuft auf dem Mac schon ein anderer Webserver, gibt es einen Konflikt.
- **Zugriff aus dem Netz:** Andere Geräte erreichen HydraHive über die IP-Adresse des Macs. Wechselt die Adresse,
  z. B. in einem anderen WLAN, passt das Zertifikat nicht mehr ganz und die Browser-Warnung kommt wieder.
- **macOS-Firewall:** Fragt macOS, ob `nginx` eingehende Verbindungen annehmen darf, klickst du **„Erlauben“**.
- **Backups:** Deine Daten liegen unter `/usr/local/var/hydrahive2`, die Einstellungen (inklusive Schlüssel) unter
  `/usr/local/etc/hydrahive2`. Diese beiden Ordner sichern. Time Machine sichert sie mit.

---

## Nützliche Befehle

| Was | Befehl |
|---|---|
| Dienst neu starten | `sudo launchctl kickstart -k system/io.hydrahive.backend` |
| Läuft der Dienst? | `sudo launchctl list \| grep io.hydrahive` |
| Läuft die Datenbank? | `brew services list \| grep postgresql` |
| Fehler-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-error.log` |
| Update-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-update.log` |
| Webserver-Fehler | `tail -50 /usr/local/var/log/nginx-hydrahive-error.log` |

### Updates

Am einfachsten im Cockpit über die Update-Funktion. Von Hand:

```bash
sudo HH_USER="$(whoami)" bash /opt/hydrahive2/installer/update-mac.sh
```

`HH_USER` muss der Benutzer sein, der installiert hat. Ohne die Angabe nimmt das Skript den Namen `admin`.

---

## Problemlösung

### `brew: command not found`
Homebrew ist nicht im Suchpfad. Führe [Schritt 4c](#4c-homebrew-dauerhaft-einrichten-wichtig) aus, schließe das
Terminal und öffne es neu.

### `… is not in the sudoers file` oder das Passwort wird nie angenommen
Dein Konto ist kein Administrator. Siehe [Schritt 2](#2-am-mac-anmelden--mit-dem-richtigen-benutzer).

### `Homebrew on macOS is only supported on Apple Silicon processors!`
Du hast einen Intel-Mac. Siehe den Kasten in [Schritt 1](#1-prüfen-welchen-mac-habe-ich) und
[Intel-Mac ohne Homebrew](#intel-mac-ohne-homebrew).

### Intel-Mac ohne Homebrew
**Notweg, von uns nicht getestet.** Die letzte Fassung des offiziellen Homebrew-Installationsskripts, die Intel
noch unterstützt hat (vom 04.08.2026), liegt weiterhin im Homebrew-Repository:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/f4aa1b1ca5b256954dbde0315455fb259cdfc45a/install.sh)"
```

Danach weiter mit 4c. Die Pfade lauten auf Intel `/usr/local/bin/brew` statt `/opt/homebrew/bin/brew`. Rechne
damit, dass einige Programme aus dem Quellcode gebaut werden und die Installation deutlich länger dauert.

### Ordner `/opt/hydrahive2` existiert schon
Von einem früheren Versuch. Ist dort **keine** laufende Installation, kannst du ihn löschen und Schritt 5
wiederholen:

```bash
sudo rm -rf /opt/hydrahive2
```

### Admin-Passwort fehlt
Der grüne Kasten zeigt `(nicht neu – siehe Anleitung)`. Dafür gibt es zwei Gründe:

1. **Du hast den Installer ein zweites Mal gestartet.** Den Benutzer `admin` gibt es dann schon, und es wird kein
   neues Passwort erzeugt. Nimm das Passwort vom ersten Mal.
2. **Der Dienst hat länger als eine Minute zum Starten gebraucht.** Dann steht das Passwort noch in einer Datei:

   ```bash
   cat /usr/local/etc/hydrahive2/.admin_initial_password
   ```

   Gibt es die Datei nicht, schau im Fehler-Log nach:

   ```bash
   grep -A3 "Erster Start" /usr/local/var/log/hydrahive2-error.log
   ```

Ändere das Passwort danach sofort (Schritt 7). Es steht sonst weiter im Log.

### Installer bricht bei `npm install` ab („network“, „ECONNRESET“)
Meist ein kurzer Netzwerk-Aussetzer beim Download. **Starte den Installer einfach nochmal**. Bereits
installierte Programme werden übersprungen.

### Browser: „Die Verbindung wurde abgelehnt“ / Seite lädt nicht
1. Läuft der Dienst? → `sudo launchctl list | grep io.hydrahive`
2. Fehler-Log ansehen → `tail -50 /usr/local/var/log/hydrahive2-error.log`
3. Dienst neu starten → `sudo launchctl kickstart -k system/io.hydrahive.backend`

### Datamining/Suche geht nicht (nach einem Neustart des Macs)
Die Datenbank startet erst nach der Anmeldung (siehe [Worauf du achten musst](#worauf-du-achten-musst)).
Melde dich an und führe dann aus:

```bash
brew services start postgresql@16
sudo launchctl kickstart -k system/io.hydrahive.backend
```

### Update meldet „git pull fehlgeschlagen“
Das passiert, wenn sich die Versionsgeschichte auf GitHub geändert hat. Die folgende Lösung verwirft **nur** lokale
Änderungen am Programmcode, nicht deine Daten:

```bash
cd /opt/hydrahive2
git fetch origin
git reset --hard origin/main
sudo HH_USER="$(whoami)" bash installer/update-mac.sh
```

### Browser zeigt nach einem Update noch die alte Oberfläche
Das liegt am Browser-Cache. Lade die Seite mit **⌘ + Shift + R** neu.

**Kommst du nicht weiter?** Frag im **#⚠️supportforum** auf unserem Discord: <https://discord.gg/GVCZvNxxFA>.
Schick am besten die letzten Zeilen aus dem Fehler-Log mit. **Mach Passwörter und Schlüssel darin vorher
unkenntlich.**

---

## Deinstallieren

```bash
sudo launchctl unload /Library/LaunchDaemons/io.hydrahive.backend.plist /Library/LaunchDaemons/io.hydrahive.nginx.plist /Library/LaunchDaemons/io.hydrahive.update.plist /Library/LaunchDaemons/io.hydrahive.restart.plist
sudo rm /Library/LaunchDaemons/io.hydrahive.*.plist
rm "$(brew --prefix)/etc/nginx/servers/hydrahive2.conf"
brew services stop postgresql@16
```

Damit ist HydraHive gestoppt und startet nicht mehr. **Deine Daten sind noch da.** Erst der folgende Befehl löscht
sie endgültig, also vorher sichern:

```bash
sudo rm -rf /opt/hydrahive2 /usr/local/var/hydrahive2 /usr/local/etc/hydrahive2
```

Die Programme aus Homebrew (Python, Node.js, PostgreSQL …) bleiben installiert. Entfernen kannst du sie bei Bedarf
mit `brew uninstall <name>`.

---

## Kurzfassung für KI-Assistenten

> Für Claude Code, ChatGPT, Codex & Co., die HydraHive auf einem Mac einrichten sollen. Menschen lesen oben.

**Regeln**
- Als **normaler Admin-Benutzer** arbeiten. **`install-mac.sh` niemals mit `sudo` starten.** `sudo` nur dort, wo es
  unten steht.
- `sudo` fragt interaktiv nach dem Mac-Passwort. **Frag den Menschen nicht nach dem Passwort im Chat.** Bitte ihn,
  es selbst im Terminal einzugeben, oder lass ihn die Befehle selbst ausführen.
- Das HydraHive-Admin-Passwort aus dem Abschluss-Kasten **nicht** in den Chat, in Dateien oder in Commits schreiben.
  Nur dem Menschen sagen, wo es steht.
- Nach jedem Schritt die **Prüfung** ausführen. Schlägt sie fehl, stopp und berichte die Ausgabe. Nicht raten.

| # | Befehl | Prüfung (erwartet) |
|---|---|---|
| 1 | `uname -m; sw_vers -productVersion` | `arm64` und ≥ 13. Bei `x86_64`: Intel → nur weiter, wenn `brew --version` schon geht, sonst Mensch fragen |
| 2 | `id -Gn \| tr ' ' '\n' \| grep -x admin` | Ausgabe `admin` |
| 3 | falls `brew` fehlt: `xcode-select --install` (GUI) und das offizielle brew.sh-Skript, danach `eval "$(/opt/homebrew/bin/brew shellenv zsh)"` + Eintrag in `~/.zprofile` | `brew --version` → `Homebrew 4.x` |
| 4 | `brew install git && sudo mkdir -p /opt/hydrahive2 && sudo chown "$(whoami)" /opt/hydrahive2 && git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2` | `test -f /opt/hydrahive2/installer/install-mac.sh && echo ok` |
| 5 | `cd /opt/hydrahive2 && bash installer/install-mac.sh` (dauert 15–45 min, fragt 1–2× nach dem sudo-Passwort) | grüner Kasten mit `URL` / `Benutzer: admin` / `Passwort` |
| 6 | — | `curl -sk https://localhost/api/health` enthält `"status":"ok"` |
| 7 | — | `sudo launchctl list \| grep io.hydrahive` zeigt `backend` und `nginx` mit PID |
| 8 | — | `brew services list \| grep postgresql@16` zeigt `started` |
| 9 | Mensch: `https://localhost` öffnen, mit `admin` anmelden, Passwort unter `/profile` ändern, unter `/llm` einen Provider anlegen | Buddy unter `/buddy` antwortet |

**Pfade:** Code `/opt/hydrahive2` · Daten `/usr/local/var/hydrahive2` · Einstellungen `/usr/local/etc/hydrahive2` ·
Logs `/usr/local/var/log/hydrahive2*.log` · Dienste `/Library/LaunchDaemons/io.hydrahive.*.plist` ·
Backend `127.0.0.1:8001`, nginx `:80`/`:443`.
**Fehler:** zuerst `tail -50 /usr/local/var/log/hydrahive2-error.log`, dann die [Problemlösung](#problemlösung).
Der Installer ist wiederholbar: Bereits installierte brew-Pakete, venv und Datenbank werden übersprungen, das Frontend wird neu gebaut.
