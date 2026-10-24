# Startseite mit Bereichen und Bereichs-Leiste

Task 7876c5df. Vorlage ist die Vorschau `preview/startdesktop` (wird nicht gemergt), von Till am 24.10.2026
freigegeben. Anker zum Zurückgehen: Tag `anker/vor-startdesktop-2026-10-24` in Kern und Modul-Repo.

## Was

1. **Startseite `/start`** mit Begrüßung, App-Suche, Buddy-Bildknopf und den Bereichs-Kacheln.
   - Ein Klick auf eine Kachel öffnet direkt die zuletzt benutzte App dieses Bereichs, beim ersten Mal die erste.
   - Eine Zwischenseite gibt es nicht.
2. **Bereichs-Leiste** ersetzt die bisherige obere Leiste (`CockpitTopbar`) überall. Aufbau:
   - ⌂ Start
   - Bereichs-Umschalter ▾ mit allen Bereichen
   - Reiter mit den Apps des aktiven Bereichs (unter `sm` ausgeblendet)
   - Kasten ⊞: Suche und alle Apps nach Bereichen, der aktuelle Bereich steht oben
   - Seitenknopf der Seite (`action`), Tresor, Hilfe, Profil
3. Der **Bereich folgt der geöffneten App** (der längste passende Pfad gewinnt). Seiten ohne Bereich
   behalten den zuletzt aktiven Bereich.
4. **Startseite nach dem Anmelden:** `/start` ist neuer Standard. Im Profil wählbar sind Start, Buddy und
   Dashboard. Die Wahl wird am Server gespeichert (`landing`).
5. **Gemerkt am Server** (`user_preferences`), damit Handy und PC gleich sind:
   - `active_area`: Kennung des Bereichs
   - `area_last`: Bereich → zuletzt benutzter Pfad
6. **Anzeigenamen der Module repariert:** `navLabel` sucht zusätzlich im Namensraum des Moduls unter dem
   Schlüssel aus `labelKey` (z. B. `aiSecurity`, `musicplayer:musicplayer`, `boardgames:bg_title`).
   Feste Namen wie in der Vorschau entfallen.

## Bereiche

| Kennung | Titel | Apps (Reihenfolge) |
|---|---|---|
| medien | Medienstudio | /studio /atelier /videoeditor /tonstudio /musicplayer /media |
| schreiben | Schreibbüro | /storyteller /notizbuch /scratchpad /diagramme /blueprint |
| wissen | Wissen & Recherche | /deepresearch /archiver /recht /datamining /memory /opentor |
| agenten | Arbeiten mit Agenten | /projects /werkstatt /buddy /tickets /settings/agents /skills /butler /zahnfee |
| kommunikation | Kommunikation | /mailbox /communication /teamchat /voip /voice |
| zuhause | Zuhause & Privat | /haushaltsbuch /akte /homeassistant /vault /cryptoboard /mining /vitrine |
| freizeit | Freizeit | /mediacenter /boardgames /minigames /vr /streaming |
| verwaltung (nur Admin) | Verwaltung | /admin /settings /dashboard /vms /containers /federation /mcp /plugins /ai-security |

- Nicht zeigen: `/example`, `/help`, `/settings/projects`.
- Alles Übrige, für den Nutzer Sichtbare landet in **Weitere** (neue Module fallen so nicht durch).
- Ein Modul kann in seinem `nav`-Eintrag das optionale Feld `area: "<kennung>"` setzen. Das hat Vorrang vor
  der Tabelle. Die Tabelle bleibt Rückfall für ältere Module (Etappe 2 trägt `area` in den Modulen ein).
- Rechte wie bisher: `visibleItems(role, access)`. Für Nicht-Admins entfällt Verwaltung, deren für alle
  sichtbare Apps landen in Weitere.

## Wie

- Neuer Ordner `frontend/src/features/startdesk/`:
  - `areas.ts`: Bereichstabelle
  - `areaLogic.ts`: reine Funktionen `fillAreas`, `areaForPath`, `entryPath`, `orderForMenu`
  - `useAreas.ts`
  - `useAreaPrefs.ts`: Server-Einstellungen, lokal sofort, Server im Hintergrund
  - `StartDeskPage.tsx`, `BuddyButton.tsx`
  - `AreaTopbar.tsx`, `AreaSwitcher.tsx`, `AreaAppsMenu.tsx`
- `CockpitTopbar` bleibt als Name und Schnittstelle (`active`, `context`, `action`, `extraActions`) erhalten,
  weil Module ihn importieren. Er zeigt die Bereichs-Leiste. Die alte Leiste wird entfernt.
- Backend: `DEFAULT_PREFERENCES` und `PreferencesOut/Patch` um `landing`, `active_area` und `area_last`
  erweitern. Geprüft wird:
  - `landing` nur aus `start | buddy | dashboard`
  - `active_area` als Kennung `^[a-z0-9-]{1,32}$` oder null
  - `area_last`: höchstens 20 Einträge, Schlüssel wie `active_area`, Werte sind Pfade `^/[A-Za-z0-9/_-]{0,120}$`
  Falsches wird verworfen (Rückfall auf den Standard), nicht mit Fehler beantwortet.
- Route `/start` im Cockpit-Rahmen (`Layout.tsx` → `cockpitPaths`). Der Index `/` leitet nach `landing`
  weiter, Standard ist `start`. Die alte Einstellung `hh_landing` im Browser wird einmal übernommen, wenn am
  Server noch nichts steht.
- Bild: `frontend/public/startdesk/buddy-knopf.webp` (Ausschnitt aus `buddy-success.mp4`).

## Akzeptanzkriterien

- Nach dem Anmelden öffnet `/` die Startseite, wenn im Profil nichts anderes gewählt ist.
- Kachel Schreibbüro öffnet `/storyteller`. Oben stehen nur Storyteller, Notizbuch, Scratchpad, Diagramme, Blueprint.
- Kasten ⊞: Der aktuelle Bereich steht oben. Die Suche „tonst“ und Enter öffnen das Tonstudio, die Leiste
  zeigt dann Medienstudio.
- Bereichs-Umschalter → „Arbeiten mit Agenten“ öffnet `/projects`.
- Zurück zur Startseite, dann Schreibbüro öffnet wieder die zuletzt benutzte App, auch nach einem Neuladen
  und in einem anderen Browser (Server).
- `/settings` zeigt den Bereich Verwaltung (Admin). Ein Nicht-Admin sieht keine Verwaltung.
- Kein Modul zeigt in Leiste oder Kasten einen rohen Schlüssel (`aiSecurity`, `musicplayer`, `bg_title`).
- Der Seitenknopf `action` (z. B. „Buddy-Settings“, „Atelier“) bleibt erreichbar.
- Bei 393, 1280 und 1600 px kein Querüberlauf, keine Seitenfehler, nichts abgeschnitten.
- Profil: Die Startseiten-Wahl wird am Server gespeichert und gilt auch in einem anderen Browser.

## Nicht enthalten

- Etappe 2: `area` in den Modul-Manifesten.
- Eigene Bereiche oder eigene Reihenfolge je Nutzer.
- „Weitergeben an …“ zwischen Apps.

## Nachtrag: Merker vor dem Laden

Gefunden im echten Test auf hydratest (24.10.): Ruft man eine App-Seite direkt auf, merkt sich die Leiste
die App, noch bevor die Einstellungen vom Server geladen sind. Dabei überschreibt sie die Merker der anderen
Bereiche am Server. Folge: Ein Bereich öffnete wieder seine erste App statt der zuletzt benutzten.

Lösung in `useAreaPrefs`:
- Vor dem Laden wird nichts gespeichert, Änderungen werden nur lokal vorgemerkt.
- Nach dem Laden werden sie mit dem Server-Stand zusammengeführt. Bei demselben Bereich gewinnt der lokale
  Wert, ein lokal gewählter Bereich gewinnt ebenfalls.
- Danach wird einmal der vollständige Stand gespeichert.
- Scheitert das Laden, gilt der lokale Stand, und Speichern bleibt möglich.
