HydraHive ist ein **selbst gehostetes KI-System**. Es läuft auf deinem eigenen Server und bringt KI-Agenten, Projekte, Gedächtnis, Automationen und Medienproduktion in einer Weboberfläche zusammen.

Man kann es sich wie ein kleines, privates KI-Team vorstellen: Jeder Nutzer hat einen persönlichen Assistenten, dazu kommen Agenten für Projekte und Spezialisten für bestimmte Aufgaben. Sie recherchieren, bearbeiten Dateien, programmieren, erzeugen Bilder und Musik, steuern das Smart Home und erinnern sich an frühere Gespräche.

## 🤖 Buddy, Projekt-Agenten, Spezialisten
- **[[Buddy]]** ist dein persönlicher Assistent und die erste Anlaufstelle. Er merkt sich, was wichtig ist, führt Aufgabenlisten und arbeitet mit Werkzeugen wie Websuche, Dateien oder Smart Home.
- **Projekt-Agenten** arbeiten in einem **[[Projekt|Projekte]]** mit eigenem Arbeitsbereich, Dateien und Git.
- **Spezialisten** bekommen von Buddy oder Projekt-Agenten einzelne Aufgaben und liefern das Ergebnis zurück.
- Erreichbar im Web-Chat und optional über WhatsApp, Discord oder per Sprache ([[Kommunikation]], [[Voice]]).

## 👨‍👩‍👧 Für wen?
**Familie und Freunde:** eigener Zugang und eigener Buddy für jeden, Alltagshelfer wie [[Notizbuch]], [[Aufgaben]], [[Haushaltsbuch]], [[Meine Akte|Meine-Akte]], [[Home Assistant|Home-Assistant]], dazu Kreatives wie Bilder, Musik und Kurzfilme. Die Daten liegen auf dem eigenen Server.

**Teams:** [[Projekte]] mit Mitgliedern und Rollen, Projekt-Agenten, ein Ticketsystem mit GitHub-Anbindung, Automationen ([[Butler]]) und [[Teamchat]].

## ⚖️ Ehrlich gesagt
- HydraHive ist **kein fertiger Dienst zum Abonnieren**. Du betreibst es selbst und nutzt eigene Zugänge zu KI-Anbietern oder lokale Modelle (z. B. über Ollama), siehe [[LLM & Modelle|LLM-und-Modelle]].
- „Selbst gehostet“ gilt für HydraHive und seine Daten. Anfragen an Cloud-Modelle, Suchdienste oder Messenger gehen an den jeweiligen Anbieter. Nur mit lokalen Modellen bleibt alles im Haus.
- Es ist **Beta**: Updates können Dinge verändern, Backups gehören dazu.

## ⚙️ Die wichtigsten Bausteine
- **Agenten & KI:** [[Agenten]], [[LLM & Modelle|LLM-und-Modelle]], [[Werkzeuge & MCP|MCP-Server]], [[Skills]], [[Gedächtnis|Gedaechtnis]], [[Datamining]]
- **Automationen:** [[Butler]] mit Auslösern, Bedingungen und Aktionen, Zeitplänen und Intervallen
- **Sicherheit:** [[Credentials]] (Zugangsdaten, die der Agent nie sieht), [[Vault]] (PIN für sensible Bereiche), [[Freigaben & Gruppen|Freigaben-und-Gruppen]]
- **Server:** [[VMs]], [[Container]], [[Compute-Nodes]], [[Archiv & Sicherung|Archiv-und-Sicherung]], Selbst-Update
- **Erweiterbar:** [[Module, Plugins & Extensions|Module]] und Themes

## 📜 Wie alles anfing
HydraHive begann Anfang 2026 mit Basteleien rund um Claude Code und einer Frage: **Wie bringt man eine KI dazu, sich morgen noch an heute zu erinnern?** Daraus entstanden nacheinander ClaudeBrain (ein externes Gedächtnis), OctopOS und HydraHive 1. Am **28. April 2026** startete HydraHive 2 als Neubau mit einer Spezifikation. Die Lehre aus den Vorgängern: Ein Agent wird nicht besser, wenn man ihm immer mehr Werkzeuge gibt. Er braucht klare Aufgaben, eigene Arbeitsbereiche und ein gut organisiertes Gedächtnis.

HydraHive ist Tills Projekt. Es war zuerst für die eigene Familie gedacht und wird jetzt nach und nach für andere geöffnet.

---
*Quelle: [README](https://github.com/hydrahive/hydrahive2.0/blob/main/README.de.md).*
