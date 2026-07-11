# HydraHive 2.0 — Benutzerhandbuch

> **Für:** Endanwender, Familien-Admins, Nicht-Entwickler  
> **Stand:** 2026-05-07  
> **Weitere Dokumente:** [Installation](#installation) · [FAQ](#häufige-fragen)

---

## Inhaltsverzeichnis

1. [Was ist HydraHive?](#was-ist-hydrahive)
2. [Erste Schritte](#erste-schritte)
3. [Die drei Agent-Typen](#die-drei-agent-typen)
4. [Chat mit deinem Agent](#chat-mit-deinem-agent)
5. [Projekte verwalten](#projekte-verwalten)
6. [Spezialisten nutzen](#spezialisten-nutzen)
7. [Skills & Fähigkeiten](#skills--fähigkeiten)
8. [Messenger-Integration](#messenger-integration)
9. [Butler (Automatisierung)](#butler-automatisierung)
10. [Datamining & Suche](#datamining--suche)
11. [Sicherheit & Privatsphäre](#sicherheit--privatsphäre)
12. [Backup & Datenexport](#backup--datenexport)
13. [Häufige Fragen](#häufige-fragen)

---

## Was ist HydraHive?

HydraHive ist dein **persönliches KI-Agenten-System**, das auf deinem eigenen Server läuft — nicht in der Cloud.

### Stell dir vor...

- Du hast einen **persönlichen KI-Assistenten** (wie Claude oder ChatGPT), aber:
  - ✅ Er läuft auf **deinem Server** — keine Daten gehen woanders hin
  - ✅ Er **vergisst nichts** — alle Gespräche bleiben erhalten
  - ✅ Er kann **wirklich arbeiten** — Dateien bearbeiten, Code schreiben, System verwalten
  - ✅ Er ist **nur für dich** — oder für deine Familie/dein Team
  - ✅ Er kann **andere Experten holen** wenn er Hilfe braucht

### Was macht HydraHive besonders?

| Funktion | HydraHive | Cloud-Dienste |
|----------|-----------|---------------|
| **Privatsphäre** | Alles lokal auf deinem Server | Daten gehen zu Konzern |
| **Kontextverlust** | ❌ Vergisst nichts | ✅ Jede Session ist neu |
| **Mehrere Nutzer** | ✅ Pro-User-Isolation | ❌ Ein Account = ein User |
| **Automatisierung** | ✅ Butler-Flows, Messenger-Bots | ❌ Nur Chat |
| **Anpassbar** | ✅ Skills, Plugins, MCP-Server | ❌ Vorgegeben |
| **Kosten** | Einmalige Server-Kosten | Monatliches Abo |

---

## Erste Schritte

### Installation (für Server-Admin)

```bash
# Auf Ubuntu 24.04 Server
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2
cd /opt/hydrahive2/installer
sudo ./install.sh
```

Nach Installation:
1. Browser öffnen: `http://<server-ip>/`
2. Initiales Admin-Passwort holen:
   ```bash
   sudo journalctl -u hydrahive2 -n 50 | grep "Erster Start"
   ```
3. Einloggen mit `admin` + angezeigtem Passwort
4. **Passwort sofort ändern** (Profil-Seite)

### Erster Login

1. **Web-UI öffnen** → `http://dein-server/`
2. **Einloggen** mit deinen Zugangsdaten
3. **Dashboard** zeigt Systemstatus

**Du siehst jetzt:**
- Deinen **Masteragent** (automatisch erstellt)
- **Chat-Interface** (klick auf "Chat" in Sidebar)
- **Agents-Seite** (um mehr Agents anzulegen)

---

## Die drei Agent-Typen

HydraHive hat drei Arten von KI-Agents — jeder für einen anderen Zweck:

### 1. 👤 Masteragent (dein persönlicher Assistent)

**Was ist das?**
- Dein **Haupt-Ansprechpartner**
- Kennt **dich** und deine Vorlieben
- Hat **Langzeitgedächtnis** (vergisst nie etwas)
- Kann **alles** — Dateien, Shell-Befehle, Web-Suche, Email

**Wann nutzen?**
- Tägliche Fragen und Aufgaben
- Planung und Organisation
- Arbeitet mit dir an Projekten
- Koordiniert andere Agents

**Beispiele:**
- *"Erstelle mir eine Einkaufsliste für Pasta Carbonara"*
- *"Fasse zusammen was wir letzte Woche über das Website-Projekt besprochen haben"*
- *"Schreibe eine Email an Till und frage nach dem Meeting-Termin"*

### 2. 📁 Projektagent (für ein spezifisches Projekt)

**Was ist das?**
- Arbeitet **nur** in einem bestimmten Projekt-Ordner
- Kennt **nur seinen Workspace** (kann nicht woanders hin)
- Hat **eigene Konfiguration** (anderes LLM-Modell, andere Tools)
- Kein persönliches Gedächtnis — fokussiert auf das Projekt

**Wann nutzen?**
- Software-Entwicklung (ein Projekt = ein Agent)
- Dokument-Bearbeitung (z.B. Buch schreiben)
- Git-Repositories verwalten

**Beispiele:**
- Projekt "Website-Relaunch" → Projektagent arbeitet nur in `/projects/website/`
- Projekt "Hausautomation" → Projektagent kennt nur seine Config-Files

### 3. 🎓 Spezialist-Agent (Domänen-Experte)

**Was ist das?**
- **Experte** für ein bestimmtes Thema (Kochen, Security, Medizin, ...)
- Wird nur **bei Bedarf geliehen** (nicht dauerhaft)
- **Lernt** aus jedem Einsatz (schreibt Notizen was funktioniert hat)
- Kann von **mehreren Usern** genutzt werden

**Wann nutzen?**
- Du brauchst Experten-Wissen (z.B. "Kochrezepte", "Netzwerk-Security")
- Masteragent oder Projektagent holt Hilfe
- Aufgabe braucht spezialisiertes Wissen

**Beispiele:**
- *"Hole den Koch-Spezialisten und frage nach vegetarischen Rezepten für 4 Personen"*
- *"Security-Spezialist soll meine nginx-Config prüfen"*

---

## Chat mit deinem Agent

### Chat-Interface

```
┌─────────────────────────────────────────────────┐
│  [Agent: Masteragent ▼]  [Modell: Claude 3.5 ▼] │  ← Header
├─────────────────────────────────────────────────┤
│                                                 │
│  👤 User:                                       │
│  Schreibe mir eine Python-Funktion die...      │
│                                                 │
│  🤖 Agent:                                      │
│  Natürlich! Hier ist die Funktion:             │
│  ```python                                      │
│  def calculate_total(items):                    │
│      return sum(i['price'] for i in items)      │
│  ```                                            │
│                                                 │
│  🔧 Tool: shell_exec                            │  ← Tool-Ausführung sichtbar
│  Command: pytest test_calculate.py             │
│  ✅ Output: All tests passed                    │
│                                                 │
├─────────────────────────────────────────────────┤
│  💬 Deine Nachricht...              [📎] [Send] │  ← Input
└─────────────────────────────────────────────────┘
```

### Funktionen

#### 📎 Dateien anhängen
- **Bilder** hochladen → Agent kann sie analysieren
- **Dokumente** (PDF, .txt) → Agent liest sie
- **Code-Files** → Agent kann sie reviewen

#### 🎤 Spracheingabe (optional)
- Mikrofon-Button → sprich deine Nachricht
- STT via Wyoming-Whisper (lokal, keine Cloud)

#### 🔊 Sprachausgabe (optional)
- Agent-Antworten werden vorgelesen
- TTS konfigurierbar (Profil-Seite)

#### 🎨 Reasoning Effort (für GPT-5 / Claude Extended Thinking)
- **Low**: Schnelle Antworten
- **Medium**: Normale Qualität
- **High**: Tiefes Nachdenken (langsamer, besser)

Wählbar im Chat-Header (nur bei Modellen mit Extended Thinking Support).

### Was kann dein Agent tun?

| Fähigkeit | Beispiel |
|-----------|----------|
| **Dateien lesen/schreiben** | *"Ändere in config.py die Zeile 23 zu X"* |
| **Shell-Befehle** | *"Installiere nginx via apt"* |
| **Web-Suche** | *"Suche nach aktuellen News zu Python 3.13"* |
| **Git-Operationen** | *"Committe die Änderungen mit Message 'Fix bug'"* |
| **Code ausführen** | *"Führe pytest aus und zeige mir die Fehler"* |
| **Andere Agents fragen** | *"Frage den Projekt-Agent nach dem Status"* |
| **Notizen schreiben** | *"Merke dir: Till mag keinen Kaffee"* |
| **Todo-Listen** | *"Setze 'README schreiben' auf die Todo-Liste"* |

**Wichtig:** Dein Agent arbeitet wie **Claude Code** — er tut was nötig ist, keine künstlichen Einschränkungen.

---

## Projekte verwalten

### Was ist ein Projekt?

Ein **Projekt** ist:
- Ein **Ordner** auf dem Server (Workspace)
- Ein **Projektagent** der nur dort arbeitet
- Optional ein **Git-Repository**
- Optional **Samba-Share** (Netzwerk-Zugriff)
- **Members** (welche User dürfen rein)

### Projekt anlegen

1. Das **Projekt-Cockpit** unter `/projects` öffnen.
2. Links das Panel **Projekt** aufklappen.
3. **+ Neues Projekt** wählen.
4. Name, Beschreibung und Projektagent festlegen.
5. Projekt anlegen; weitere Zugriffe und Integrationen anschließend projektbezogen konfigurieren.

**Was passiert:**
- Ein eigener Projekt-Workspace wird erstellt.
- Ein Projektagent wird angelegt und an den Workspace gebunden.
- Das Projekt wird als aktiver Cockpit-Kontext gespeichert.

### Projekt verwalten

Alle Fachaktionen liegen bewusst im linken Panel **Projekt**, nicht in der globalen Topbar:

- **Bearbeiten** — Basisdaten, Status, Notizen und kontrolliertes Löschen
- **Verwalten → Zugriff** — Members und Spezialisten
- **Verwalten → Server** — Server, VMs und Container
- **Verwalten → Mounts** — SMB- und Netzwerkfreigaben
- **Verwalten → Git** — Init, Clone, Commit, Remotes, Pull und Push
- **Verwalten → Integrationen** — MCP, Plugins, LLM-Projekt-Key und Samba
- **Auswerten** — Statistiken, Sessions und Audit

Bestehende Secrets werden im Cockpit nicht offengelegt. Insbesondere werden gespeicherte Git-Tokens, vorhandene LLM-Projekt-Keys und Samba-Passwörter nicht angezeigt.

### Globale Cockpit-Menüs

Die obere Leiste enthält nur globale Funktionen: Cockpit-Wechsel, **Apps**, kontextuelle **Hilfe** und das Benutzermenü mit Profil, Einstellungen und Abmelden. Auf kleinen Displays liegen diese Funktionen in einem Drawer.

### Mit Projekt arbeiten

**Im Chat:**
```
User: Arbeite an Projekt "Website-Relaunch"
Agent: Wechsle zu Projekt-Agent...
       [AgentLink übernimmt]
Project-Agent: Hallo! Ich bin der Agent für Website-Relaunch.
               Was soll ich tun?
```

**Oder direkt:**
- Projekte-Seite → Projekt auswählen → "Chat öffnen"

### Projekt-Workspace via Samba

**Wenn Samba aktiviert:**
1. **Windows**: `\\dein-server\hydrahive-projekt-name`
2. **Mac**: `smb://dein-server/hydrahive-projekt-name`
3. **Login**: Dein HydraHive-Username + Passwort

Jetzt kannst du Dateien im Projekt direkt bearbeiten (z.B. mit VSCode, Word, etc.).

---

## Spezialisten nutzen

### Spezialist anlegen

1. **Agents-Seite** → **"Neuer Spezialist"**
2. **Name** (z.B. "Koch-Experte")
3. **Domäne** beschreiben (z.B. "Vegetarische Küche, mediterrane Rezepte")
4. **Skills** zuweisen (z.B. "Rezept-Datenbank", "Nährwert-Berechnung")
5. **LLM-Modell** wählen (kann anders sein als Masteragent)

### Spezialist nutzen

**Über ask_agent-Tool:**
```
User: Frage den Koch-Spezialisten nach einem vegetarischen Rezept für 4 Personen

Agent: [nutzt ask_agent-Tool]
       → AgentLink leitet Anfrage an Koch-Spezialisten
       → Koch-Spezialist antwortet mit Rezept
       → Antwort zurück an Masteragent

Agent: Der Koch-Spezialist empfiehlt:
       Auberginen-Moussaka mit Feta...
```

**Direkt chatten:**
- Agents-Seite → Spezialist auswählen → "Chat öffnen"

### Was Spezialisten besonders macht

- ✅ **Lernen**: Nach jedem Einsatz schreiben sie Notizen (was hat funktioniert, was nicht)
- ✅ **Mehrfach-Nutzung**: Mehrere User können denselben Spezialisten nutzen
- ✅ **Domain-Fokus**: Spezialisierte Skills und Prompts
- ✅ **On-Demand**: Wird nicht dauerhaft betrieben, nur bei Bedarf

---

## Skills & Fähigkeiten

### Was sind Skills?

**Skills** sind wiederverwendbare **Verhaltensmuster** — wie Rezepte die dem Agent sagen "so gehst du vor".

**Beispiele:**
- `code-review` → Wie macht man gutes Code-Review
- `debugging` → Strukturierte Bug-Suche
- `git-workflow` → Saubere Git-Commits
- `refactor` → Code-Qualität verbessern

### Skill nutzen

**Im Chat:**
```
User: Nutze den Skill "code-review" für die Datei app.py

Agent: [lädt code-review-Skill]
       Ich führe jetzt einen strukturierten Code-Review durch:
       
       1. Lesbarkeit prüfen...
       2. Sicherheit checken...
       3. Performance analysieren...
       
       Ergebnis: 3 Warnungen gefunden...
```

**Oder automatisch:**
- Agent erkennt selbst wann ein Skill passt
- Skill wird geladen und ausgeführt

### Eigene Skills erstellen

**Als Markdown-Datei:**
```markdown
---
name: mein-skill
description: Macht etwas Cooles
when_to_use: Wenn User X fragt
---

# Anleitung für den Agent

1. Mache zuerst Y
2. Dann prüfe Z
3. Gib Ergebnis zurück im Format...
```

**Hochladen:**
- Skills-Seite → "Neuer Skill" → Markdown-Datei hochladen
- Agent kann Skill jetzt nutzen

---

## Messenger-Integration

### WhatsApp

**Was geht:**
- Agent antwortet auf WhatsApp-Nachrichten
- Bilder analysieren ("Was ist auf dem Foto?")
- Dateien empfangen und verarbeiten

**Einrichtung:**
1. **System-Seite** → **WhatsApp** → **QR-Code scannen**
2. WhatsApp-App öffnen → **Einstellungen** → **Verknüpfte Geräte**
3. QR-Code scannen
4. Fertig! Jetzt kann dein Masteragent WhatsApp empfangen

**Filter einrichten:**
- Nur bestimmte Kontakte → Agent antwortet nur auf ausgewählte Personen
- Nur Gruppen → Agent antwortet nur in bestimmten WhatsApp-Gruppen
- Keyword-Filter → Nur wenn Nachricht "!hydra" enthält

### Discord

**Was geht:**
- Bot in Discord-Server einladen
- Agent antwortet auf Mentions (`@HydraHive wie spät ist es?`)
- Slash-Commands (`/ask Erkläre mir Quantenphysik`)

**Einrichtung:**
1. **System-Seite** → **Discord**
2. **Bot-Token** eingeben (von Discord Developer Portal)
3. **Server auswählen**
4. **Fertig!**

### Telegram

**Was geht:**
- Bot in Telegram-Chats nutzen
- Private Nachrichten an Bot
- Gruppen-Chat mit Bot

**Einrichtung:**
1. **System-Seite** → **Telegram**
2. **Bot-Token** eingeben (von @BotFather)
3. **Fertig!**

### Matrix (selbst gehostet)

**Was geht:**
- Eigener Matrix-Homeserver (conduwuit)
- Agent als Matrix-Bot
- E2E-verschlüsselt (optional)

**Einrichtung:**
- Admin-Sache (siehe Admin-Handbuch)

---

## Butler (Automatisierung)

### Was ist Butler?

**Butler** ist ein visueller Flow-Builder — du erstellst **Regeln** ohne Code:

```
Wenn [Trigger] → Prüfe [Bedingung] → Führe [Aktion] aus
```

**Beispiele:**
- *"Wenn neue Email von Till → Leite an Masteragent → Fasse zusammen und schicke Telegram-Nachricht"*
- *"Jeden Montag 9 Uhr → Erstelle Todo-Liste für die Woche"*
- *"Wenn Datei in /projects/website/ geändert wird → Git-Commit → Slack-Notification"*

### Flow erstellen

1. **Butler-Seite** öffnen
2. **"Neuer Flow"** klicken
3. **Trigger** wählen:
   - ⏰ **Zeit** (Cron: täglich, wöchentlich, ...)
   - 📧 **Email** (neue Email empfangen)
   - 📁 **Datei** (Datei geändert, erstellt, gelöscht)
   - 💬 **Messenger** (WhatsApp/Discord/Telegram-Nachricht)
   - 🌐 **Webhook** (HTTP POST von extern)

4. **Bedingung** hinzufügen (optional):
   - 🔍 **Regex-Match** (Text enthält "wichtig")
   - ⏱️ **Zeitfenster** (nur zwischen 9-17 Uhr)
   - 👤 **User-Match** (nur wenn von User X)

5. **Aktion** wählen:
   - 🤖 **Agent ausführen** (Masteragent beauftragen)
   - 📧 **Email senden**
   - 💬 **Messenger-Nachricht**
   - 🌐 **HTTP POST** (Webhook an externe API)
   - 📝 **Log schreiben**

6. **Aktivieren** → Flow läuft ab jetzt

### Beispiel-Flow (Backup-Reminder)

```
Trigger:  ⏰ Cron: "0 20 * * 0" (Jeden Sonntag 20 Uhr)
    ↓
Bedingung: [keine]
    ↓
Aktion:   💬 Telegram-Nachricht an Admin:
          "Backup erstellen! Letzte Woche vergessen?"
```

---

## Datamining & Suche

### Was ist Datamining?

**Datamining** durchsucht **alle deine Gespräche** mit Agents — findet was du vor Wochen besprochen hast.

**Features:**
- 🔍 **Volltextsuche** — finde Nachrichten mit bestimmten Wörtern
- 🧠 **Semantische Suche** — finde *ähnliche* Themen (auch ohne exakte Wörter)
- 📊 **Timeline** — was habe ich im November gemacht?
- 🕸️ **Knowledge Graph** — Wissenskarte aller Gespräche (visuell)

### Suche nutzen

**Datamining-Seite öffnen:**

#### 1. Volltextsuche
```
Suche: "Python Tutorial"
Filter: Von 2025-01-01 bis heute
        Agent: Masteragent

Ergebnisse:
• [2025-11-03] Session mit Masteragent
  "...habe ich dir ein Python-Tutorial geschickt..."
  
• [2025-12-15] Session mit Project-Agent
  "...Python-Tutorial für Flask fertig..."
```

#### 2. Semantische Suche
```
Suche: "Wie koche ich Pasta?"

Ergebnisse (ähnliche Themen):
• [2025-10-20] "Rezept für Spaghetti Carbonara"
• [2025-11-05] "Kochzeit für Nudeln"
• [2025-12-01] "Italienische Küche Tipps"
```

→ Findet **inhaltlich Ähnliches**, auch wenn Wörter anders sind!

#### 3. Timeline
```
Zeitraum: 2025-11-01 bis 2025-11-30

November 2025:
├─ 2025-11-03: 3 Sessions (Python, Website-Projekt, Backup)
├─ 2025-11-10: 1 Session (Rezepte)
├─ 2025-11-20: 5 Sessions (Code-Review, Git, Docker, ...)
└─ 2025-11-28: 2 Sessions (Jahresplanung, Geschenke)
```

#### 4. Knowledge Graph
```
[Visueller Graph]

Nodes:
• "Python" ──┬── "Flask Tutorial"
             ├── "Pytest"
             └── "Docker-Integration"

• "Website" ─── "nginx Config"
              └── "Tailwind CSS"

Klick auf Node → zeigt alle Sessions zu diesem Thema
```

**Wie funktioniert das?**
- Alle Nachrichten werden **embeddet** (in Vektoren umgewandelt)
- UMAP reduziert auf 2D
- HDBSCAN clustert nach Themen
- D3.js visualisiert als interaktiven Graph

---

## Sicherheit & Privatsphäre

### Wer sieht was?

| Rolle | Kann sehen | Kann NICHT sehen |
|-------|-----------|------------------|
| **Admin** | Alles (Logs, User, System) | Private Agent-Chats ohne Erlaubnis |
| **User** | Eigene Agents, eigene Projekte, eigene Sessions | Andere User-Daten |
| **Projekt-Member** | Projekt-Dateien, Projekt-Agent-Chats | Andere Projekte |

### Passwort-Sicherheit

- ✅ **bcrypt-Hashing** (Cost 12)
- ✅ **Failed-Login-Lockout** (5 Versuche → 15 Min Sperre)
- ✅ **Kein Klartext** — Passwörter werden nie gespeichert

**Passwort ändern:**
1. Profil-Seite → "Passwort ändern"
2. Altes Passwort + neues Passwort eingeben
3. Speichern

### Tool-Bestätigung (Safety-Feature)

**Problem:** Agent soll nicht einfach `rm -rf /` ausführen ohne zu fragen.

**Lösung:** Pro Agent konfigurierbar:

```
Agent-Settings → Tool-Bestätigung: AN
```

**Wenn aktiviert:**
- Agent fragt **vor jedem Tool-Call** um Erlaubnis
- Du siehst im Chat:
  ```
  ⚠️ Agent möchte ausführen:
      Tool: shell_exec
      Command: rm important_file.txt
      
      [Allow] [Deny]
  ```
- Klick auf **Allow** → Tool wird ausgeführt
- Klick auf **Deny** → Tool wird abgebrochen
- Keine Antwort nach 5 Min → automatisch Deny

**Wann nutzen?**
- Produktions-Server (nichts kaputt machen)
- Wenn Agent neue Tools bekommt (erst testen)
- Shared Agents (mehrere User nutzen denselben)

**Wann NICHT nutzen?**
- Dev-Umgebung (nervt nur)
- Trusted Personal Agent (du vertraust ihm)

### Daten-Isolation

**Pro-User:**
- Jeder User hat **eigenen Masteragent**
- **Eigene Projekte** (nicht sichtbar für andere)
- **Eigene Sessions** (kein User sieht fremde Chats)

**Pro-Projekt:**
- Projektagent sieht **nur seinen Workspace**
- Kein Zugriff auf `/home/`, `/etc/`, andere Projekte
- Git-Repo ist **isoliert**

**Spezialisten:**
- **Geteilt** zwischen Usern (bewusst)
- Lernen aus allen Einsätzen
- Kein User-spezifisches Memory

---

## Backup & Datenexport

### User-Backup (DSGVO: Datenportabilität)

**Was ist das?**
- Du lädst **alle deine Daten** herunter
- Format: `.tar.gz` (unverschlüsselt)
- Kann auf anderem HydraHive-Server wiederhergestellt werden

**Was ist drin?**
- ✅ Alle deine Agents (Config + Memory + Workspace)
- ✅ Alle deine Projekte (Code + Git-History)
- ✅ Alle deine Sessions (Chats, Tool-Calls, alles)
- ✅ Butler-Flows
- ✅ MCP-Server-Configs
- ✅ WhatsApp-Filters (wenn genutzt)

**Backup erstellen:**
1. **Profil-Seite** → **"Backup erstellen"**
2. Warte (kann bei großen Projekten dauern)
3. Download: `hydrahive-backup-<username>-<datum>.tar.gz`
4. **Sicher ablegen!** (USB-Stick, Cloud, verschlüsselt)

**Backup wiederherstellen:**
1. **Profil-Seite** → **"Backup hochladen"**
2. Datei auswählen → **"Restore"**
3. System prüft Backup → stellt alles wieder her

**WICHTIG:**
- Backup ist **unverschlüsselt** — du musst es selbst verschlüsseln
- Backup auf **anderem Server** verwenden → funktioniert (DSGVO-Portabilität)
- Restore **überschreibt** vorhandene Daten (Vorsicht!)

### System-Backup (nur Admin)

**Was ist das?**
- **Kompletter Server-Zustand**
- Alle User, alle Projekte, alle Configs

**System-Backup erstellen:**
1. **System-Seite** (nur Admin) → **"System-Backup"**
2. Download: `hydrahive-system-backup-<datum>.tar.gz`

**System-Restore:**
1. **System-Seite** → **"System-Backup hochladen"**
2. Datei auswählen → **"Restore"**
3. **Server startet neu!**

**Use-Cases:**
- Server-Migration (alter Server → neuer Server)
- Disaster-Recovery (Festplatte kaputt)
- Vor riskanten Updates

---

## Häufige Fragen

### Allgemein

**Q: Brauche ich einen eigenen Server?**  
A: Ja. HydraHive läuft auf Ubuntu 24.04 (empfohlen: min. 2 GB RAM, 20 GB Disk). Kann auch Raspberry Pi 5 sein.

**Q: Kann ich HydraHive ohne Linux-Kenntnisse nutzen?**  
A: **Installation** braucht Linux-Grundkenntnisse (oder Hilfe vom Admin). **Nutzung** ist rein Web-UI — kein Terminal nötig.

**Q: Kostet HydraHive etwas?**  
A: Software ist **kostenlos** (MIT-Lizenz). Du zahlst nur:
- Server-Hosting (oder eigene Hardware)
- LLM-API-Kosten (Anthropic, OpenAI, etc.)

**Q: Welche LLM-Provider funktionieren?**  
A: Anthropic (Claude), OpenAI (GPT-4o, GPT-5), Groq, MiniMax, Gemini, Mistral, OpenRouter, NVIDIA NIM, Deepseek.

**Q: Kann ich mehrere LLM-Provider gleichzeitig nutzen?**  
A: Ja! Jeder Agent kann ein anderes Modell nutzen. Masteragent = Claude 3.5, Projektagent = GPT-4o, Spezialist = Deepseek.

---

### Agenten

**Q: Wie viele Agents kann ich haben?**  
A: Unbegrenzt. Du hast **einen Masteragent** (automatisch), kannst aber beliebig viele Projekt- und Spezialisten-Agents erstellen.

**Q: Vergisst mein Agent nach langer Zeit was?**  
A: **Nein!** HydraHive nutzt **Compaction** — alte Gespräche werden zusammengefasst, aber nie gelöscht. Agent erinnert sich an alles.

**Q: Kann ich einen Agent löschen?**  
A: Ja. Agents-Seite → Agent auswählen → "Löschen". **Vorsicht:** Alle Sessions, Memory, Workspace werden gelöscht (irreversibel, außer du hast Backup).

**Q: Kann ein Agent auf mein ganzes System zugreifen?**  
A: **Masteragent:** Ja (wie Claude Code — volle Tool-Macht). **Projektagent:** Nur auf seinen Workspace. **Spezialist:** Konfigurierbar (Admin entscheidet).

---

### Projekte

**Q: Kann ich Git-Repos von außen (GitHub, GitLab) nutzen?**  
A: Ja! Projekt-Workspace kann ein `git clone` von GitHub sein. Agent kann pushen/pullen (GitHub-Token in Projekt-Config).

**Q: Kann ich Dateien im Projekt mit VSCode bearbeiten?**  
A: Ja! Via **Samba-Share** (Windows/Mac/Linux) oder **SFTP** (VSCode Remote). Projekt-Workspace ist normaler Ordner auf dem Server.

**Q: Was passiert wenn zwei User gleichzeitig am selben Projekt arbeiten?**  
A: **Projekt-Agent** arbeitet sequenziell (ein Chat = ein Durchlauf). Workspace-Dateien können parallel bearbeitet werden (wie bei normalem Git).

---

### Sicherheit

**Q: Sind meine Daten verschlüsselt?**  
A: **Im Transit:** Ja (HTTPS, wenn konfiguriert). **At Rest:** Nein (Datenbank/Files sind unverschlüsselt auf Disk). Server-Verschlüsselung ist Admin-Aufgabe (LUKS, etc.).

**Q: Kann ein anderer User meine Chats sehen?**  
A: **Nein.** Pro-User-Isolation — kein User sieht fremde Sessions (außer Admin mit DB-Zugriff).

**Q: Kann Admin meine Nachrichten mitlesen?**  
A: Technisch **ja** (Admin hat Server-Zugriff). Aber: HydraHive ist für **Familien/Teams** gedacht wo du dem Admin vertraust (z.B. du selbst bist Admin).

**Q: Was passiert wenn mein Passwort geleakt wird?**  
A: **Sofort ändern!** Profil-Seite → Passwort ändern. Admin kann auch Passwort zurücksetzen.

---

### Messenger

**Q: Sieht WhatsApp dass ich einen Bot nutze?**  
A: HydraHive nutzt **WhatsApp-Web-API** (wie wenn du WhatsApp am PC nutzt). WhatsApp sieht es als "verknüpftes Gerät".

**Q: Kann ich WhatsApp-Nachrichten filtern?**  
A: Ja! Filter nach Kontakt, Gruppe, Keyword. Nur gefilterte Nachrichten gehen an Agent.

**Q: Antwortet Agent auf ALLE Discord-Nachrichten?**  
A: Nur wenn **@HydraHive** erwähnt wird oder Slash-Command (`/ask`). Sonst ignoriert er.

---

### Backup & Export

**Q: Wie oft sollte ich Backup machen?**  
A: **User-Backup:** Wöchentlich (wenn viel gearbeitet). **System-Backup (Admin):** Vor Updates, monatlich.

**Q: Kann ich Backup auf anderem Server wiederherstellen?**  
A: Ja! User-Backup ist **portabel** — funktioniert auf jedem HydraHive-Server (DSGVO-Portabilität).

**Q: Ist Backup verschlüsselt?**  
A: **Nein.** Du bekommst `.tar.gz` (unverschlüsselt). **Du** musst es verschlüsseln (z.B. mit `gpg` oder 7-Zip mit Passwort).

---

### Performance

**Q: Wie schnell antwortet der Agent?**  
A: Hängt vom **LLM-Provider** ab. Claude/GPT-4o: ~2-5 Sek erste Antwort. Groq (Llama): <1 Sek. Lange Antworten streamen live.

**Q: Kann HydraHive auf Raspberry Pi laufen?**  
A: Ja! Raspberry Pi 5 (8 GB RAM) ist getestet. Performance gut für 1-3 User.

**Q: Werden alte Sessions langsamer?**  
A: **Nein.** Compaction sorgt dafür dass Context-Window konstant bleibt. Auch nach 1000 Nachrichten = gleiche Speed.

---

### Datamining

**Q: Kann ich nach Sessions von vor 2 Jahren suchen?**  
A: **Ja!** Datamining durchsucht **alle Sessions** (solange DB nicht gelöscht). Timeline-Filter: `2024-01-01` bis `2024-12-31`.

**Q: Was ist der Knowledge Graph?**  
A: Visueller Graph der **alle Themen** zeigt über die du gesprochen hast. Nodes = Themen, Edges = Zusammenhänge. Klick auf Node → Sessions zu dem Thema.

**Q: Brauche ich PostgreSQL für Datamining?**  
A: **Nein** für Volltextsuche. **Ja** für Knowledge Graph + Semantische Suche (optional, Admin muss aktivieren).

---

### Updates

**Q: Wie update ich HydraHive?**  
A: **Admin** klickt in Web-UI auf "System-Update" → Server zieht `git pull`, baut neu, startet neu (automatisch). Oder manuell: `sudo /opt/hydrahive2/installer/update.sh`.

**Q: Gehen meine Daten beim Update verloren?**  
A: **Nein.** Updates ändern nur Code, nie Daten. **Aber:** Vor großen Updates **Backup machen** (Sicherheit).

---

## Weitere Hilfe

- 📖 **Entwickler-Doku:** [ARCHITECTURE.md](ARCHITECTURE.md)
- 📋 **Vollständige Spec:** [SPEC.md](../SPEC.md)
- 💬 **GitHub Issues:** [github.com/hydrahive/hydrahive2.0/issues](https://github.com/hydrahive/hydrahive2.0/issues)
- 📧 **Support:** (Community-Forum, Discord — noch in Planung)

---

**Viel Spaß mit deinem persönlichen KI-Agenten-System! 🐝**
