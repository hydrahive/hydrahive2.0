# HydraHive auf dem Mac installieren – Schritt für Schritt

> **Status: experimentell.** HydraHive läuft auf dem Mac, der Mac-Installer ist aber einfacher als der
> Linux-Installer. Einige Funktionen gibt es auf dem Mac nicht (siehe [Was auf dem Mac nicht geht](#was-auf-dem-mac-nicht-geht)).
> Für einen Server, der rund um die Uhr läuft, empfehlen wir Linux (Ubuntu).
> Zuletzt getestet: 23.10.2026 auf einem Intel-iMac (macOS 15.3) und einem MacBook Air M2 (macOS 27): Neuinstallation,
> Umzug älterer Installationen per Update, Container, Tailscale und Voice.

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
  [Dateien im Finder](#dateien-im-finder-projekt-im-netz-freigeben) ·
  [Nützliche Befehle](#nützliche-befehle) · [Problemlösung](#problemlösung) · [Deinstallieren](#deinstallieren) ·
  [Kurzfassung für KI-Assistenten](#kurzfassung-für-ki-assistenten)

---

## 0. Bevor du anfängst – die wichtigsten Fragen

| Frage | Antwort |
|---|---|
| **Wie lange dauert das?** | 30–60 Minuten. Das meiste ist Warten auf Downloads. |
| **Muss ich programmieren können?** | Nein. Du kopierst Befehle aus dieser Anleitung in das Programm **Terminal**. Jeder Befehl steht hier zum Kopieren. |
| **Brauche ich einen speziellen Benutzer?** | **Nein, aber einen Administrator.** Du installierst mit deinem normalen Mac-Benutzerkonto, wenn es Administratorrechte hat. HydraHive selbst läuft danach unter einem eigenen, versteckten Konto `_hydrahive`, das der Installer anlegt (siehe [Schritt 6](#6-installer-starten--und-was-dann-passiert)). Dein Konto braucht HydraHive weiter für Homebrew. |
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

> **Ein eigenes Konto für HydraHive musst du nicht anlegen.** Das erledigt der Installer: HydraHive läuft unter dem
> versteckten Systemkonto `_hydrahive` (siehe [Schritt 6](#6-installer-starten--und-was-dann-passiert)).

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
> wenn er es braucht. Homebrew gehört dir und verweigert das Systemkonto „root“.

> ℹ️ **HydraHive bekommt ein eigenes Konto.** Der Installer legt ein verstecktes Systemkonto `_hydrahive` an. Es
> taucht nicht im Anmeldefenster auf und hat kein Passwort. HydraHive läuft unter diesem Konto, nicht unter deinem
> Benutzer. Der Grund: Ab macOS 15 sperrt der Datenschutz „Lokales Netzwerk“ alle Programme des angemeldeten
> Benutzers für das Heimnetz, auch Hintergrund-Dienste. Unter dem eigenen Konto erreicht HydraHive Geräte im Heimnetz
> (Portfreigaben, Home Assistant, andere Rechner), und HydraHive kommt nicht an deine privaten Dateien.

### Was du im Terminal siehst

Der Installer arbeitet in Phasen. Jede beginnt mit einer türkisen Zeile `[hh2-mac] Phase …`:

| Phase | Was passiert | Dauer (ca.) | Musst du etwas tun? |
|---|---|---|---|
| **0** Dienst-Konto | Legt das versteckte Konto `_hydrahive` an | Sekunden | **ja: `Password:` → Mac-Passwort** |
| **1** System-Dependencies | Installiert Python 3.12, Node.js, git, ffmpeg, GitHub-CLI, `uv` und `mmx-cli` | 5–20 min | nein |
| **2** Verzeichnisse | Legt Ordner für Daten und Einstellungen an | Sekunden | **ja: `Password:` → Mac-Passwort** |
| **3** Python-venv + Backend | Richtet das Programm im Hintergrund ein | 2–5 min | nein |
| **4** Frontend | Baut die Weboberfläche | 3–10 min | nein |
| **5** PostgreSQL | Installiert die Datenbank für Gedächtnis und Suche und richtet sie als Hintergrund-Dienst ein | 2–5 min | **evtl. `Password:`** |
| **6 / 6b** launchd-Service | Richtet HydraHive als Hintergrund-Dienst ein, der beim Hochfahren startet | Sekunden | **evtl. nochmal `Password:`** (auch in Phase 7 möglich) |
| **6c** AgentLink | Richtet AgentLink ein, damit Agenten sich gegenseitig Aufträge geben und Server sich koppeln können (eigene Datenbank im PostgreSQL, zwei Hintergrund-Dienste) | 2–5 min | **evtl. `Password:`** |
| **6d** Container (optional) | Nur mit `--with=containers`: kleine Linux-VM mit Incus (Colima), siehe [Container](#container-optional) | 3–10 min | nein |
| **6e** Tailscale (optional) | Nur mit `--with=tailscale`: baut Tailscale ohne App und richtet es als Dienst ein, siehe [Tailscale](#tailscale-optional) | 1–3 min | nein |
| **6f** Voice (optional) | Nur mit `--with=voice`: Spracheingabe und Vorlesen direkt auf dem Mac, siehe [Voice](#voice-optional) | 1–5 min | nein |
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
   Für das **Gedächtnis** (Buddy findet frühere Gespräche auch, wenn andere Wörter benutzt wurden) braucht es dort
   zusätzlich ein **Embedding-Modell**, z. B. `text-embedding-3-small` (OpenAI) oder `baai/bge-m3` (OpenRouter).
   Ohne Embedding-Modell findet die Suche nur Stellen, in denen das gesuchte Wort genau vorkommt.
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

Erwartet sind acht Zeilen mit `io.hydrahive.backend`, `io.hydrahive.nginx`, `io.hydrahive.postgres`,
`io.hydrahive.agentlink`, `io.hydrahive.agentlink-frontend`, `io.hydrahive.update`, `io.hydrahive.restart` und
`io.hydrahive.addon`. Mit den Zusatz-Modulen kommen `io.hydrahive.colima` (Container), `io.hydrahive.tailscaled`
(Tailscale) und `io.hydrahive.voice-stt` / `io.hydrahive.voice-tts` (Voice) dazu. Steht in der ersten Spalte eine
**Zahl**, läuft der Dienst. Ein `-` ist bei `update`, `restart` und `addon` normal, die laufen nur bei Bedarf.

> **Installation von vor Oktober 2026?** Dann fehlt AgentLink (die zwei `agentlink`-Zeilen). Ein normales Update im
> Cockpit (Einstellungen → System → Update) richtet es nach.

```bash
curl -sk https://localhost/api/health
```

Erwartet ist eine Zeile mit `"status":"ok"`.

```bash
"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1
```

Erwartet: `127.0.0.1:5432 - accepting connections` (die Datenbank). Ist der Mac auf Deutsch eingestellt, steht dort
`Verbindungen werden angenommen`.

```bash
curl -s http://127.0.0.1:9000/health
```

Erwartet: `"status":"healthy"` und `"redis":"memory"` (AgentLink). Auf dem Mac läuft AgentLink ohne Redis – Homebrew
bietet Redis für Intel-Macs nur noch zum Selbstbauen an, das würde Stunden dauern. Im Cockpit zeigt die Startseite
„AgentLink verbunden“.

---

## Was auf dem Mac nicht geht

Der Mac-Installer richtet nur den **Kern** ein. Folgendes gibt es auf dem Mac **nicht** (oder nur von Hand):

| Funktion | Auf dem Mac | Warum |
|---|---|---|
| **Container** (Incus) | ✅ optional | über eine kleine Linux-VM (Colima), siehe [Container](#container-optional) |
| **VMs** (libvirt/QEMU) | ❌ nicht verfügbar | gibt es nur unter Linux |
| **Voice** (Spracheingabe + Vorlesen) | ✅ optional | direkt auf dem Mac, ohne Container: Einstellungen → Zusatz-Module → Voice (oder `--with=voice`), siehe [Voice](#voice-optional) |
| **WhatsApp-Anbindung** | ❌ nicht eingerichtet | Bridge wird nur vom Linux-Installer aufgesetzt |
| **Projektordner im Netz freigeben** (wie Samba) | ✅ optional | über die macOS-Dateifreigabe: Einstellungen → Zusatz-Module → Samba-Freigaben / Dateifreigabe, siehe [Dateien im Finder](#dateien-im-finder-projekt-im-netz-freigeben) |
| **Tailscale-Fernzugriff & Server-Kopplung** | ✅ optional | automatisch über Einstellungen → Zusatz-Module → Tailscale (oder `--with=tailscale`), siehe [Tailscale](#tailscale-optional). Alternativ die Tailscale-App – **nicht beides** |
| **Websuche (SearXNG)** | ⚠️ nicht automatisch | eigene SearXNG-Adresse in den Einstellungen eintragen, sonst funktioniert `web_search` nicht |
| **Start-Agenten & MCP-Server** | ⚠️ nicht automatisch | Linux legt sie beim Installieren an, auf dem Mac von Hand im Cockpit anlegen |
| **Lokale Medien-Modelle** (Bild/Video mit NVIDIA-GPU) | ❌ nicht verfügbar | braucht NVIDIA + Docker |
| **Erweiterungen** (Einstellungen → Erweiterungen) | ⚠️ meist nicht | viele brauchen `apt`/`docker` und brechen mit einer unklaren Fehlermeldung ab |
| **Module** (Einstellungen → Module) | ✅ fast alle | getestet: 21 von 22; **OpenTor** geht nicht (Tor nur über Linux-Pakete) |
| **Firewall-Regeln** (ufw) | ❌ | macOS nutzt eine eigene Firewall |

**Was gut geht:** Cockpit, Buddy, Agenten, Projekte, Werkstatt, Datamining/Gedächtnis, Aufgaben, AgentLink (Agenten
beauftragen sich gegenseitig), Module wie Atelier, Storyteller, Haushaltsbuch usw. und Updates über das Cockpit.

---

## Worauf du achten musst

- **Der Mac muss wach bleiben.** HydraHive läuft nur, solange der Mac an ist und **nicht schläft**. Für Dauerbetrieb:
  **Systemeinstellungen → Energie** (beim Laptop: **Batterie → Optionen**) → Ruhezustand bei ausgeschaltetem
  Display verhindern. Laptops am Netzteil lassen.
- **Nach einem Neustart** starten HydraHive, Webserver und Datenbank von selbst, auch ohne dass sich jemand
  anmeldet.
- **Das Konto `_hydrahive` nicht löschen.** HydraHive läuft unter diesem Konto. Deinen eigenen Benutzer braucht
  HydraHive nur für Homebrew (Programme wie Python, Datenbank, nginx gehören dir).
- **Dateien aus deinem Benutzer-Ordner** (Schreibtisch, Dokumente …) sieht HydraHive nicht. Was HydraHive bearbeiten
  soll, lädst du im Cockpit hoch – oder du gibst das Projekt im Netz frei und legst die Dateien im Finder hinein
  (siehe [Dateien im Finder](#dateien-im-finder-projekt-im-netz-freigeben)).
- **Ports 80 und 443** belegt HydraHive (nginx). Läuft auf dem Mac schon ein anderer Webserver, gibt es einen Konflikt.
- **Zugriff aus dem Netz:** Andere Geräte erreichen HydraHive über die IP-Adresse des Macs. Wechselt die Adresse,
  z. B. in einem anderen WLAN, passt das Zertifikat nicht mehr ganz und die Browser-Warnung kommt wieder.
- **macOS-Firewall:** Fragt macOS, ob `nginx` eingehende Verbindungen annehmen darf, klickst du **„Erlauben“**.
- **Backups:** Deine Daten liegen unter `/usr/local/var/hydrahive2`, die Einstellungen (inklusive Schlüssel) unter
  `/usr/local/etc/hydrahive2`. Diese beiden Ordner sichern. Time Machine sichert sie mit.

---

## Container (optional)

HydraHive kann auf dem Mac Container verwalten – in der Oberfläche (**Container**) und durch Agenten (`incus …`),
genau wie unter Linux. Dafür läuft im Hintergrund eine kleine **Linux-VM** (Colima mit Incus).

**Einschalten** – einer der beiden Wege:
- bei der Installation: `bash installer/install-mac.sh --with=containers`
- später: **Einstellungen → Zusatz-Module → Container → Installieren** (dauert einige Minuten)

| | Standard | ändern mit |
|---|---|---|
| Kerne der VM | 2 | `HH_CONTAINERS_CPU` (höchstens die Hälfte des Macs) |
| Arbeitsspeicher der VM | 4 GB | `HH_CONTAINERS_MEMORY` (höchstens die Hälfte des Macs) |
| Platz für Container | 60 GB | `HH_CONTAINERS_DISK` |

**Gut zu wissen:**
- Die VM belegt dauerhaft Arbeitsspeicher (etwa 1–2 GB tatsächlich genutzt). Deshalb ist die Option standardmäßig aus.
- Netz: Container hängen im eigenen Netz 10.10.0.0/24 (wie auf einem VPS). Ins Heimnetz direkt einbinden
  (Modus „bridged“) geht auf dem Mac nicht.
- **Ports freigeben** (Container → Ports): „öffentlich“ lauscht auf allen Adressen des Macs, „Tailnet“ nur auf der
  Tailscale-Adresse. Nur **TCP**. Der Container sieht als Absender die VM, nicht den echten Besucher.
- Nach einem Neustart des Macs startet die VM von selbst (Dienst `io.hydrahive.colima`), auch ohne Anmeldung.
  Freigegebene Ports sind spätestens 30 Sekunden nach dem Start von HydraHive wieder erreichbar.
- Echte VMs (nicht Container) gibt es auf dem Mac nicht.

**Prüfen:**

```bash
sudo launchctl list | grep io.hydrahive.colima
cd /tmp && sudo -u _hydrahive env HOME=/usr/local/var/hydrahive2/home COLIMA_HOME=/usr/local/var/hydrahive2/colima /usr/local/lib/hydrahive2/containers/bin/incus list
```

Die VM gehört dem Konto `_hydrahive`. Als dein eigener Benutzer findet `incus` sie nicht.

Probleme: Log unter `/usr/local/var/log/hydrahive2-colima.log` bzw. `hydrahive2-addon.log`.

---

## Tailscale (optional)

Tailscale verbindet den Mac sicher mit deinen anderen Geräten und Servern – für den Zugriff von unterwegs und für
die **Kopplung mit einem anderen HydraHive** (Agenten beauftragen Agenten auf dem anderen Server).

**Einschalten:** Einstellungen → Zusatz-Module → **Tailscale → Installieren** (oder bei der Installation
`--with=tailscale`). HydraHive baut Tailscale dafür einmal selbst (etwa 1–3 Minuten) und richtet es als Dienst ein,
der beim Hochfahren startet – **ohne die Tailscale-App** und ohne Freigabe am Bildschirm.

**Anmelden:** Einstellungen → System → Tailscale → **„Im Browser anmelden“** → Link öffnen → mit deinem
Tailscale-Konto anmelden. Alternativ „Mit Auth-Key verbinden“.

**Gut zu wissen:**
- Ist die **Tailscale-App** schon installiert, nutzt HydraHive sie und installiert nichts zusätzlich. Beide
  gleichzeitig vertragen sich nicht.
- Diese Variante kann einen fremden Exit-Node nicht nutzen; Taildrop geht nur eingeschränkt. Für Fernzugriff und
  Kopplung reicht sie vollständig. Updates kommen mit dem normalen HydraHive-Update.
- Prüfen: `sudo launchctl list | grep io.hydrahive.tailscaled`, Log `/usr/local/var/log/hydrahive2-tailscaled.log`.

---

## Dateien im Finder (Projekt im Netz freigeben)

Die Projektordner liegen unter `/usr/local/var/hydrahive2/workspaces/projects/`. Dieser Ordner gehört dem
Dienst-Konto `_hydrahive` – mit deinem eigenen Konto kommst du dort im Finder **nicht** hinein. Das ist Absicht:
Niemand braucht dafür ein Terminal oder Admin-Rechte. Stattdessen gibst du einzelne Projekte im Netz frei, wie unter
Linux mit Samba:

1. **Einmal einrichten:** Einstellungen → Zusatz-Module → **Samba-Freigaben / Dateifreigabe → Installieren**. HydraHive schaltet die
   macOS-Dateifreigabe (SMB) ein und legt ein eigenes Konto **`hhshare`** an. Dieses Konto kann sich am Mac nicht
   anmelden und hat keine Shell – es ist nur für die Freigaben da.
2. **Projekt freigeben:** Projekt öffnen → Einstellungen bzw. Integrationen → **Projekt im Netz freigeben** → **Aktiviert** einschalten. Dort
   stehen Adresse, Benutzer und Passwort.
3. **Am Mac selbst (ohne Passwort):** Finder → dein **Benutzerordner** (das Haus-Symbol, ⇧⌘H) → Ordner
   **„HydraHive“** → das Projekt. Dort liegen nur die Projekte, die du freigegeben hast. Tipp: den Ordner in die
   Seitenleiste des Finders ziehen.

   > Warum nicht „Mit Server verbinden“? Der Finder verbindet sich **nicht** mit dem Mac, auf dem er selbst läuft
   > („Server nicht erreichbar“ – auch mit `localhost` oder der eigenen Adresse). Das ist macOS, kein Fehler von
   > HydraHive.
4. **Von anderen Rechnern im Netz:**
   - **Anderer Mac:** Finder → Menü **Gehe zu → Mit Server verbinden** (⌘K) → `smb://<Adresse des Macs>/<Freigabe>` →
     „Registrierter Benutzer“ → Benutzer `hhshare` und das Passwort aus dem Cockpit.
   - **Windows:** Explorer → Adresszeile `\\<Adresse des Macs>\<Freigabe>`.

**Gut zu wissen:**
- Freigegeben wird nur, was du im Projekt einschaltest – nie der ganze Daten-Ordner, nie Einstellungen oder Datenbank.
- Schaltest du die Freigabe aus, verschwindet das Projekt auch wieder aus dem Ordner „HydraHive“.
- Die Zugangsdaten gelten für alle freigegebenen Projekte (eigene Zugänge je Mitarbeiter folgen).
- Was du über die Freigabe ablegst, sieht HydraHive sofort – und umgekehrt.
- Prüfen: Systemeinstellungen → Allgemein → Teilen → **Dateifreigabe** ist an; Log
  `/usr/local/var/log/hydrahive2-shares.log`.

---

## Voice (optional)

Spracheingabe (Mikrofon im Chat, Sprachnachrichten, `transcribe_audio`) und Vorlesen – lokal, ohne Cloud.

**Einschalten:** Einstellungen → Zusatz-Module → **Voice → Installieren** (oder bei der Installation
`--with=voice`). Container braucht es dafür auf dem Mac **nicht**: Spracherkennung (Whisper) und Vorlesestimme (Piper)
laufen als zwei Hintergrund-Dienste direkt auf dem Mac und starten beim Hochfahren mit.

**Gut zu wissen:**
- Dauer etwa 1–5 Minuten. Beim ersten Start lädt die Spracherkennung ihr Sprachmodell (~460 MB).
- Platz etwa 1,1 GB, Arbeitsspeicher etwa 400 MB, solange der Dienst läuft.
- Updates kommen mit dem normalen HydraHive-Update.
- Prüfen: `sudo launchctl list | grep io.hydrahive.voice`, Logs
  `/usr/local/var/log/hydrahive2-voice-stt.log` und `…-voice-tts.log`.

---

## Nützliche Befehle

| Was | Befehl |
|---|---|
| Dienst neu starten | `sudo launchctl kickstart -k system/io.hydrahive.backend` |
| Läuft der Dienst? | `sudo launchctl list \| grep io.hydrahive` |
| Läuft die Datenbank? | `"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1` |
| Datenbank neu starten | `sudo launchctl kickstart -k system/io.hydrahive.postgres` |
| Datenbank-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-postgres.log` |
| Zusatz-Module-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-addon.log` |
| Fehler-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-error.log` |
| Update-Log ansehen | `tail -50 /usr/local/var/log/hydrahive2-update.log` |
| Webserver-Fehler | `tail -50 /usr/local/var/log/nginx-hydrahive-error.log` |

### Updates

Am einfachsten im Cockpit über die Update-Funktion. Von Hand:

```bash
sudo bash /opt/hydrahive2/installer/update-mac.sh
```

Das Skript erkennt den Dienst-Benutzer selbst.

**Ältere Installationen** (vor dem eigenen Konto) zieht das nächste Update einmalig auf `_hydrahive` um. Das dauert
einige Minuten; HydraHive ist währenddessen kurz nicht erreichbar. Vorher legt das Update eine Sicherung an
(`/usr/local/var/hydrahive2-backup-<datum>`: Einstellungen, Chats, Datenbank). Klappt ein Schritt nicht, stellt es den
alten Stand wieder her und versucht es beim nächsten Update erneut. Wer den Umzug nicht möchte, schreibt
`HH_SERVICE_ACCOUNT=no` in `/usr/local/etc/hydrahive2/install.conf`.

**Befehle im HydraHive-Ordner** (z. B. `git`) laufen jetzt als das Konto:

```bash
cd /tmp && sudo -H -u _hydrahive git -C /opt/hydrahive2 log --oneline -3
```

`cd /tmp` und `-H` sind wichtig: sonst beschwert sich git über deinen eigenen Benutzer-Ordner. Als dein eigener
Benutzer meldet git „dubiose Besitzverhältnisse“, denn der Ordner gehört jetzt dem Konto.

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
   sudo cat /usr/local/etc/hydrahive2/.admin_initial_password
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

### Datamining/Suche geht nicht
1. Läuft die Datenbank? → `"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1`
2. Wenn nicht: `sudo launchctl kickstart -k system/io.hydrahive.postgres`, dann
   `sudo launchctl kickstart -k system/io.hydrahive.backend`
3. Datenbank-Log ansehen → `tail -50 /usr/local/var/log/hydrahive2-postgres.log`
   (Installationen ohne eigenes Konto: `tail -50 "$(brew --prefix)/var/log/postgresql@16.log"`)
4. Die Suche findet nur genaue Wörter, aber nichts Ähnliches? Dann fehlt ein **Embedding-Modell**, siehe
   [Schritt 8](#8-ki-einrichten-sonst-antwortet-buddy-nicht). Im Fehler-Log steht dann `Embedding None` oder
   `Batch-Embedding fehlgeschlagen`.

**Ältere Installation (vor Oktober 2026)?** Dort startete die Datenbank erst nach der Anmeldung. Ein Update
(Cockpit oder `sudo bash /opt/hydrahive2/installer/update-mac.sh`) stellt das einmalig um.

### Update meldet „git pull fehlgeschlagen“
Das passiert, wenn sich die Versionsgeschichte auf GitHub geändert hat. Die folgende Lösung verwirft **nur** lokale
Änderungen am Programmcode, nicht deine Daten:

```bash
cd /tmp
sudo -H -u _hydrahive git -C /opt/hydrahive2 fetch origin
sudo -H -u _hydrahive git -C /opt/hydrahive2 reset --hard origin/main
sudo bash /opt/hydrahive2/installer/update-mac.sh
```

Bei Installationen ohne eigenes Konto (`HH_SERVICE_ACCOUNT=no`) lässt du `sudo -H -u _hydrahive` weg.

### Installer oder Zusatz-Modul bricht mit `tapi error` / `unknown architecture` ab
Apples Kommandozeilen-Werkzeuge passen nicht zur macOS-Version. Das passiert oft nach einem großen macOS-Update.
Im Log steht etwa `ld: tapi error: malformed file … unknown architecture arm64e.x1-macos` oder
`clang: error: linker command failed`. Werkzeuge neu installieren:

```bash
sudo rm -rf /Library/Developer/CommandLineTools
xcode-select --install
```

Im Fenster „Installieren“ klicken, warten und danach den Installer bzw. das Zusatz-Modul noch einmal starten.
Tailscale und Voice (auf Apple-Macs) brauchen diese Werkzeuge nicht mehr. Die Datenbank-Erweiterung bei der
ersten Installation und Voice auf Intel-Macs werden aber noch selbst gebaut.

### Browser zeigt nach einem Update noch die alte Oberfläche
Das liegt am Browser-Cache. Lade die Seite mit **⌘ + Shift + R** neu.

**Kommst du nicht weiter?** Frag im **#⚠️supportforum** auf unserem Discord: <https://discord.gg/GVCZvNxxFA>.
Schick am besten die letzten Zeilen aus dem Fehler-Log mit. **Mach Passwörter und Schlüssel darin vorher
unkenntlich.**

---

## Deinstallieren

```bash
for p in /Library/LaunchDaemons/io.hydrahive.*.plist; do sudo launchctl unload "$p"; done
sudo rm /Library/LaunchDaemons/io.hydrahive.*.plist
rm "$(brew --prefix)/etc/nginx/servers/hydrahive2.conf"
```

Damit ist HydraHive gestoppt und startet nicht mehr. **Deine Daten sind noch da.** Erst die folgenden Befehle löschen
sie endgültig, also vorher sichern:

```bash
sudo rm -rf /opt/hydrahive2 /opt/hydralink /usr/local/var/hydrahive2 /usr/local/etc/hydrahive2 /usr/local/etc/hydralink
sudo rm -rf /usr/local/lib/hydrahive2
sudo rm -f /usr/local/var/log/hydrahive2*.log /usr/local/var/log/agentlink*.log /usr/local/var/log/nginx-hydrahive*.log
```

`/usr/local/lib/hydrahive2` enthält die Programme für Container, Tailscale und Voice. Sicherungen vom Umzug auf das
eigene Konto liegen unter `/usr/local/var/hydrahive2-backup-<datum>`. Die löschst du von Hand, wenn du sie nicht mehr
brauchst.

Zum Schluss das Konto `_hydrahive` entfernen:

```bash
sudo dscl . -delete /Users/_hydrahive
sudo dscl . -delete /Groups/_hydrahive
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
| 7 | — | `sudo launchctl list \| grep io.hydrahive` zeigt `backend`, `nginx`, `postgres`, `agentlink` und `agentlink-frontend` mit PID |
| 8 | — | `"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1` → `accepting connections` |
| 9 | Mensch: `https://localhost` öffnen, mit `admin` anmelden, Passwort unter `/profile` ändern, unter `/llm` einen Provider anlegen | Buddy unter `/buddy` antwortet |

**Konto:** Dienste laufen als verstecktes Systemkonto `_hydrahive` (UID 450–499). Code, Daten und Einstellungen gehören
ihm. Homebrew gehört dem Menschen. `git`/`incus` im HydraHive-Ordner: `cd /tmp && sudo -H -u _hydrahive …`.
`/usr/local/etc/hydrahive2` (inkl. `install.conf`) ist nur mit `sudo` lesbar.
**Pfade:** Code `/opt/hydrahive2` · AgentLink `/opt/hydralink` · Daten `/usr/local/var/hydrahive2` ·
Einstellungen `/usr/local/etc/hydrahive2` · Datenbank `/usr/local/var/hydrahive2/postgres` ·
Logs `/usr/local/var/log/hydrahive2*.log` · Dienste `/Library/LaunchDaemons/io.hydrahive.*.plist` ·
Backend `127.0.0.1:8001`, AgentLink `127.0.0.1:9000`, nginx `:80`/`:443`.
**Fehler:** zuerst `tail -50 /usr/local/var/log/hydrahive2-error.log`, dann die [Problemlösung](#problemlösung).
Der Installer ist wiederholbar: Bereits installierte brew-Pakete, venv und Datenbank werden übersprungen, das Frontend wird neu gebaut.
