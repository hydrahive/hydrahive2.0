# Projekt-Cockpit

## Was ist ein Projekt?

Ein Projekt ist ein abgegrenzter Arbeitskontext mit eigenem Workspace, Projektagent, Mitgliedern, Sessions und optionalen Git-, Server- und Netzwerkverbindungen. Der Projektagent arbeitet nur im zugehörigen Workspace.

## Orientierung

- **Mitte:** projektgebundener Chat
- **Links:** Projektwahl, Projektaktionen, Agenten, Git-Status und KI-Einstellungen
- **Rechts:** Git-Baum, Workspace-Dateien und Tasks

Das aktive Projekt wird serverseitig als Benutzerpräferenz gespeichert.

## Projekt auswählen und Aktionen finden

1. Links das Panel **Projekt** aufklappen.
2. Projekt in der Auswahl wählen.
3. Unter Beschreibung und Auswahl findest du die Projektaktionen.

Ist das Panel eingeklappt, sind auch die Aktionen verborgen. Sie stehen bewusst nicht in der globalen Topbar.

### Direkt sichtbar

- **+ Neues Projekt** — Projekt mit zugehörigem Projektagent anlegen
- **Bearbeiten** — Name, Beschreibung, Status und Notizen ändern; Projekt kontrolliert löschen

### Verwalten

- **Zugriff** — Members und Spezialisten verwalten
- **Server** — Server, VMs und Container zuweisen oder entfernen
- **Mounts** — SMB-/Netzwerkfreigaben erstellen und zuweisen
- **Git** — Repository initialisieren oder klonen, Commits, Remotes, Pull und Push
- **Integrationen** — MCP-Server-IDs, erlaubte Plugins, LLM-Projekt-Key und Samba

### Auswerten

- **Statistiken** — Sessions, Nachrichten, Tokens und letzte Aktivität
- **Sessions** — vollständige Projekt-Sessionliste; Klick öffnet die Werkstatt
- **Audit** — Aktivitäten nach Aktion und Benutzer filtern

## Globale Topbar

Die obere Leiste ist für globale Funktionen reserviert:

- Wechsel zwischen Projekte, Buddy, Media, Vault und Admin
- **Apps** öffnet alle für deine Rolle erlaubten Bereiche
- **Hilfe** öffnet diese kontextuelle Hilfe
- Das Benutzermenü öffnet Profil und Einstellungen oder meldet dich ab

Auf kleinen Displays erscheint die Navigation in einem rechten Drawer.

## Sicherheit

- Löschen und Entfernen verlangen eine Bestätigung.
- Git-Tokens werden nicht angezeigt.
- Ein vorhandener LLM-Projekt-Key wird nicht in das Formular geladen; er kann ersetzt oder explizit entfernt werden.
- Das Samba-Passwort wird im Project-Cockpit weder angezeigt noch kopiert.
- Member sehen nur Projekte, auf die sie Zugriff haben; Admins sehen alle.

## Typische Probleme

- **Projektaktionen fehlen:** Panel **Projekt** links aufklappen.
- **User kann nicht hinzugefügt werden:** Der Account muss zuerst in der Benutzerverwaltung existieren.
- **Pull/Push deaktiviert:** Repository benötigt ein Remote; Push ist ohne ausstehende Commits deaktiviert.
- **Mount oder Server fehlt:** Nur verfügbare und für dich erlaubte Ressourcen werden angeboten.

## Tipp

Nutze pro größerem Vorhaben ein eigenes Projekt. So bleiben Workspace, Agent, Sessions, Git-Verlauf und Zugriffsrechte sauber getrennt.
