# Projekt-Cockpit: Reiter auf schmalen Bildschirmen

## Was

Unter 1280 px Breite (unter Tailwind `xl`) zeigt das Projekt-Cockpit (`/projects`) eine Reiterleiste
**Projekt · Chat · Dateien & Tasks**. Sichtbar ist immer nur der gewählte Bereich, und der bekommt die
volle Höhe. Ab 1280 px bleibt die Ansicht wie bisher: drei Spalten nebeneinander, keine Reiterleiste.

## Warum

Task 1841e0df: Auf dem iPhone 16 (Chrome und Safari) liegen beide Seitenleisten über und unter dem Chat.
Vom Chat sind nur Kopfzeile und Eingabe zu sehen, der Verlauf nicht. Das Raster
`xl:grid-cols-[270px_minmax(420px,1fr)_360px]` (seit c3b86801) hat unter `xl` nur eine Spalte. Dann
werden alle drei Bereiche untereinander in eine feste Bildschirmhöhe gepresst.

Gemessene Höhe des Chat-Bereichs (hydratest, Playwright):

| Bildschirm | Höhe |
|---|---|
| 393×852 | 104 px |
| 768–1279 px Breite | 68 px |
| 1280×800 | 669 px |

## Wie

- Neuer Zustand `mobileTab` mit den Werten `project`, `chat` und `files`. Standard ist `chat`.
  Der Zustand gilt nur für die laufende Seite und wird nicht gespeichert.
- `project/ProjectMobileTabs.tsx`:
  - Reiterleiste mit `role="tablist"` und je Reiter `role="tab"`, `aria-selected` und `aria-controls`.
  - Die Leiste trägt `xl:hidden`.
  - Texte über i18n (`projects:cockpit_tabs.*`, de/en).
- Reine Hilfsfunktion `mobileTabs.ts → paneClass(tab, active, wideDisplay)`:
  - Ist der Bereich aktiv, liefert sie keine Klasse zum Verstecken.
  - Ist er nicht aktiv, liefert sie `hidden xl:block` bzw. `hidden xl:grid`.
  - Ab `xl` ist so immer alles sichtbar. Die Reiter-Wahl wirkt sich dort nicht aus.
- Raster: `grid-rows-1`. Die eine Zeile füllt die volle Höhe (`minmax(0,1fr)`), auch wenn unter `xl` nur ein
  Bereich sichtbar ist.
- Rechte Spalte: unter `xl` scrollbar (`overflow-y-auto`), ab `xl` wie bisher `overflow-hidden` mit den
  drei Zeilen.
- Automatischer Wechsel zum Reiter **Chat**:
  - wenn im Reiter Projekt ein Agent gewählt wird,
  - wenn eine Sitzung mit einem Agenten gestartet wird,
  - wenn aus einer Übersicht eine Sitzung geöffnet wird.

## Akzeptanzkriterien

- Bei 393×852 ist der Chat-Bereich auf `/projects` mindestens 600 px hoch, und der Chatverlauf ist sichtbar.
- Bei 1024×768 ist der Chat-Bereich mindestens 550 px hoch.
- Bei 1280 und 1600 px Breite sind alle drei Spalten wie bisher nebeneinander, die Reiterleiste fehlt.
- Ein Tipp auf „Projekt“ oder „Dateien & Tasks“ zeigt den jeweiligen Bereich in voller Höhe und scrollbar.
- Wer einen Agenten wählt, landet im Reiter Chat.
- Es gibt keinen horizontalen Überlauf bei 393 px.

## Nicht enthalten

- Werkstatt- und Buddy-Chat: Dort ist der Verlauf auf dem Handy sichtbar. Kleinere Mängel
  (abgeschnittene Knöpfe, überdeckter Hilfe-Knopf) kommen in einen eigenen Schritt.
- Wischgesten zwischen den Reitern.
