# HydraHive Cockpits

Die Cockpits sind die primären Arbeitsoberflächen von HydraHive. Sie liegen auf eigenen Routen und verwenden eine gemeinsame, responsive globale Topbar.

## Routen

| Cockpit | Route | Zweck |
|---|---|---|
| Projekte | `/projects` | Projektarbeit, Chat, Agenten, Git, Dateien, Tasks und Projektverwaltung |
| Buddy | `/buddy` | Persönlicher Assistent und Buddy-Widgets |
| Media | `/media` | Projektgebundene Medienproduktion |
| Vault | `/vault` | Geschützte Daten- und Dokumentarbeitsfläche |
| Admin | `/admin` | System- und Verwaltungsübersicht, nur für Admins |

## Globale Topbar

Die Topbar enthält ausschließlich globale Navigation und globale Funktionen:

- Wechsel zwischen den Cockpits
- **Apps**: rollenbasierter Launcher aus der zentralen HydraHive-Navigation
- **Hilfe**: öffnet den vorhandenen HelpDrawer passend zum aktuellen Cockpit
- **Benutzermenü**: Benutzername, Rolle, Profil, Einstellungen und Abmelden

Auf mittleren Displays werden zusätzliche Aktionen im Menü **Aktionen** gebündelt. Auf kleinen Displays erscheinen Navigation und globale Funktionen in einem rechten Drawer. Escape und ein Klick auf den Hintergrund schließen offene Menüs.

## Project-Cockpit

Das aktive Projekt wird links im Panel **Projekt** ausgewählt. Ist das Panel eingeklappt, sind auch die Projektaktionen verborgen. Die globale Topbar enthält bewusst keine Projekt-Fachaktionen.

### Direkt im Projektpanel

- **+ Neues Projekt**
- **Bearbeiten**: Name, Beschreibung, Status, Notizen und kontrolliertes Löschen

### Verwalten

- **Zugriff**: Mitglieder und Spezialisten
- **Server**: Server, VMs und Container zuweisen oder entfernen
- **Mounts**: SMB-/Netzwerkfreigaben erstellen und zuweisen
- **Git**: Init, Clone, Commit, Remotes, Pull, Push und kontrolliertes Entfernen
- **Integrationen**: MCP-Server-IDs, erlaubte Plugins, LLM-Projekt-Key und Samba

### Auswerten

- **Statistiken**: Sessions, Nachrichten, Tokens und letzte Aktivität
- **Sessions**: vollständige Projekt-Sessionliste mit Sprung in die Werkstatt
- **Audit**: Projektaktivitäten mit Aktions- und Benutzerfilter

### Arbeitsflächen

- Mitte: vollwertiger projektgebundener Chat
- Links: Projektwahl, Projektagenten, Git-Status und KI-Einstellungen
- Rechts: Git-Baum, Workspace-Dateien und Projekt-Tasks

## Sicherheit

- Projektaktionen verwenden die bestehenden APIs und Berechtigungsprüfungen.
- Entfernen und Löschen verlangen weiterhin eine Bestätigung.
- Gespeicherte Git-Tokens werden nicht angezeigt.
- Ein bestehender LLM-Projekt-Key wird nicht in das Formular geladen; er kann nur ersetzt oder explizit entfernt werden.
- Das Samba-Passwort wird im Project-Cockpit weder angezeigt noch kopiert.
- Butler-/Webhook-Projektintegration ist nicht Teil des aktuellen Integrations-Overlays, da dafür noch kein eigener abgesicherter Backend-Slice existiert.

## Alte Projekteinstellungen

`/settings/projects` bleibt als Verwaltungs- und Kompatibilitätsoberfläche erreichbar. Für die tägliche Projektarbeit ist `/projects` die primäre Oberfläche. Neue Cockpit-Funktionen sollen bestehende APIs und Fachkomponenten wiederverwenden, nicht parallel neu implementieren.
