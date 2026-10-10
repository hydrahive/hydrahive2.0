# Plugins: neue Version anzeigen und aktualisieren – wie bei den Modulen

Stand 10.10.2026 · Task 6c8ac3c7 · Till: „das sollten wir ändern, dass es angezeigt wird, wenn es was neues gibt, wie
bei den Modulen auch“.

## Anlass
`file-search` 0.2.0 lag im Plugin-Hub, installiert war 0.1.1. In der Plugin-Verwaltung (Admin-Cockpit → Integrationen →
Plugins) war das nicht zu sehen:
- Der Reiter „Hub“ zeigte v0.2.0 mit einem ausgegrauten „Neu installieren“.
- Im Reiter „Installiert“ stand v0.1.1 mit einem „Aktualisieren“-Knopf, der immer gleich aussieht – egal ob es etwas
  Neues gibt.
- Es gab weder einen Hinweis in der Fußzeile noch einen Hinweis darauf, dass nach einem Update ein Neustart fehlt.

## Vorbild Module (bleibt unverändert)
- `GET /api/modules` frischt den Hub-Cache auf und liefert je Modul `version`, `available_version` und `update_available`
  (Versionsvergleich `installer.is_update_available`).
- `GET /api/modules/update-count` liest nur den vorhandenen Cache (kein git) und speist den Zähler in der Fußzeile.
- Die Karte zeigt die Plakette „vX → vY“ und den Knopf „Update verfügbar“; im Kopf des Fensters gibt es „Alle updaten“.

## Plugins: neu
### Server
- `GET /api/plugins/installed` liefert je Plugin zusätzlich:
  - `installed_version`: Version aus der `plugin.yaml` auf der Platte.
  - `available_version`: Version laut Hub-Index im Cache (`hub.json`).
  - `update_available`: `available_version` ist neuer als `installed_version` (gleicher Vergleich wie bei Modulen).
  - `restart_needed`: Die Version auf der Platte unterscheidet sich von der geladenen (`version`). Das tritt nach
    „Aktualisieren“ ein: Neuer Code liegt auf der Platte, geladen bleibt der alte bis zum Neustart.

  Der Cache wird dafür nicht aufgefrischt (kein git). Das Auffrischen übernimmt `GET /api/plugins/hub`, das die
  Oberfläche beim Öffnen sowieso aufruft; danach wird die Liste neu geladen.
- `GET /api/plugins/update-count` (Admin): Anzahl der Plugins mit `update_available`, nur aus dem Cache. Fehler ergeben
  0 und werfen nie.
- Fehlt der Cache oder ist er kaputt, ist `available_version` = `null` und es wird kein Update gemeldet. Die Liste der
  installierten Plugins bleibt intakt.

### Oberfläche
- **Karte „Installiert“:**
  - Bei `update_available` erscheint die gelbe Plakette „v0.1.1 → v0.2.0“, und der Knopf heißt „Update verfügbar“
    (gelb hervorgehoben).
  - Bei `restart_needed` erscheint die Plakette „Neustart nötig“ statt „Update verfügbar“.
- **Karte „Hub“:** Ist das Plugin installiert und gibt es eine neue Version, gibt es statt des ausgegrauten
  „Neu installieren“ den Knopf „Update verfügbar“, der dasselbe tut wie „Aktualisieren“.
- **Fensterkopf:** „Alle updaten“, wenn mindestens ein Update verfügbar ist.
- **Reiter-Beschriftung:** „Installiert (4 · 1 Update)“, wenn Updates verfügbar sind.
- **Fußzeile (nur Admin):** neben dem Modul-Zähler ein Plugin-Zähler. Ein Klick öffnet Admin-Cockpit → Plugins
  (`/admin?section=plugins`). Abgefragt wird wie bei den Modulen alle 15 Minuten.
- Gilt für das Cockpit-Fenster (`PluginsOverlay`) und die alte Seite `/settings/plugins` (`PluginsPage`), beide über
  `usePlugins`.

## Nicht in dieser Etappe
- Plugins ohne Neustart neu laden (Python-Module bleiben im Speicher; es bleibt beim Hinweis plus Neustart-Knopf).
- Automatisches Aktualisieren.

## Akzeptanz
- Mit installiertem 0.1.1 und 0.2.0 im Hub: Plakette, Knopf „Update verfügbar“ (auch im Reiter Hub), Zähler im Reiter
  und in der Fußzeile.
- Nach „Aktualisieren“ ohne Neustart: „Neustart nötig“, kein „Update verfügbar“ mehr, Fußzeilen-Zähler 0.
- Nach dem Neustart: keine Plakette.
- Ohne Hub-Cache: Liste wie bisher, kein Update gemeldet, kein Fehler.
- Browser-Test auf hydratest mit echtem Plugin-Hub, über genau den Klickweg, der Till genannt wird.
