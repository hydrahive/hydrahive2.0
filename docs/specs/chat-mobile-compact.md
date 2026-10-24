# Chat auf dem Handy: kompakter Kopf, kompakte Eingabe, Hilfe-Knopf in der Fußzeile

## Was

Unter 640 px Breite (unter Tailwind `sm`):

- **Chat-Kopf** (`_ChatHeader.tsx`, im Projekt-Cockpit und in der Werkstatt):
  - Die Knöpfe „Komprimieren“, „Neuer Chat“ und „Hilfe“ zeigen nur ihr Symbol. Der Text bleibt als
    `aria-label` und `title` erhalten.
  - Der Füllstand (`TokenMeter`) und die Sitzungsnummer sind ausgeblendet.
  - Die Auswahl der Projekt-Sitzung ist höchstens 140 px breit.
- **Eingabe** (`MessageInput.tsx`):
  - Der Hinweis „Enter zum Senden · Shift+Enter für neue Zeile“ ist ausgeblendet.
  - Die Befehls-Knöpfe (help, clear, compact …) stehen in einer Zeile, die sich seitlich wischen lässt.
    Keiner wird abgeschnitten.
- **Hilfe-Assistent:**
  - Der schwebende runde „?“-Knopf (`HelpAssistantView`) ist ausgeblendet.
  - Stattdessen öffnet ein kleiner „?“-Knopf in der Fußzeile (`AppFooter`) denselben Assistenten.

Ab 640 px bleibt alles wie bisher.

## Warum

Folge aus Task 1841e0df (#616). Gemessen bei 393×852 auf dem Stand f69d5eda (Task 37232294):

| Seite | Kopf | Eingabe | Verlauf | Probleme |
|---|---|---|---|---|
| Projekte | 111 px | 152 px | 397 px | „?“ überdeckt `title`, `system` abgeschnitten |
| Werkstatt | 52 px | 152 px | 548 px | „Neuer Chat“ abgeschnitten, „?“ überdeckt `tokens` und `title` |
| Buddy | 58 px | 152 px | 469 px | „?“ überdeckt `model` und `character`, `character` abgeschnitten |

Gründe:
- Im Kopf bricht der Text in mehrere Zeilen um, weil die Knöpfe mit voller Beschriftung den Platz belegen.
- Der Hinweis unter der Eingabe braucht zwei Zeilen.
- Der „?“-Knopf liegt fest unten rechts über jedem Inhalt.

## Wie

- Beschriftung der Knöpfe: `<span className="hidden sm:inline">`. Der Knopf selbst trägt `aria-label`.
- `HelpButton` (`i18n/HelpButton.tsx`): Die Beschriftung ist unter `sm` ausgeblendet, `aria-label` wird ergänzt.
  Das gilt überall, wo der Knopf vorkommt.
- `TokenMeter`: Hülle `hidden sm:flex`.
- Hinweis unter der Eingabe: `hidden sm:block`.
- Zeile mit den Befehls-Knöpfen: `min-w-0 flex-nowrap overflow-x-auto`, die Knöpfe mit `shrink-0`.
- Hilfe öffnen über ein Ereignis:
  - `helpApi.ts` exportiert `HELP_TOGGLE_EVENT = "hh:help-toggle"` und `requestHelpToggle()`.
  - `HelpAssistant` hört auf das Ereignis und schaltet den Assistenten auf und zu.
  - `AppFooter` zeigt unter `sm` einen „?“-Knopf (`sm:hidden`, `data-help-footer`), der `requestHelpToggle()`
    aufruft.
  - Der schwebende Knopf trägt `hidden sm:flex`.
- Die Auswahl der Projekt-Sitzung wandert in eine eigene Datei `_SessionMenu.tsx`.
  So bleibt `_ChatHeader.tsx` unter etwa 200 Zeilen.

## Akzeptanzkriterien

Bei 393×852 (Projekte mit leerer Test-Sitzung, Werkstatt, Buddy):

- Projekte: Chat-Kopf höchstens 64 px, Eingabe höchstens 110 px, Verlauf mindestens 480 px.
- Werkstatt und Buddy: Eingabe höchstens 110 px.
- Kein sichtbarer Knopf im Chat ist abgeschnitten. Die Befehlszeile darf wischbar sein und zählt nicht
  als abgeschnitten.
- Kein Knopf im Chat wird vom Hilfe-Knopf überdeckt.
- Der „?“-Knopf in der Fußzeile öffnet den Hilfe-Assistenten.
- Kein Querüberlauf.

Bei 1280 und 1600 px:

- Beschriftungen „Komprimieren“ und „Neuer Chat“, Füllstand, Hinweis und schwebender „?“-Knopf sind sichtbar.
- Der Fußzeilen-Knopf ist nicht sichtbar.

## Nicht enthalten

- Die eingeklappten Seitenstreifen der Werkstatt (je 32 px) bleiben.
- Der Inhalt der Befehls-Knöpfe ändert sich nicht.

## Nachtrag: Werkstatt-Rahmen und Modellzeile

Gefunden bei der Browser-Prüfung:

- **Werkstatt ragt über den Rahmen:**
  - `ThreePanelLayout` gleicht mit `-m-4 md:-m-6` und `h-[calc(100%+2rem/3rem)]` den alten Seitenabstand aus
    (4ab3d865, 01.06.).
  - Seit 0e6df831 (18.09.) sitzt die Werkstatt in einem Rahmen mit `p-[10px]`. Deshalb ragt die Ansicht auf
    allen Breiten 6–14 px über den Rahmen, und der Knopf „Aufklappen“ ist angeschnitten.
  - Lösung: `ThreePanelLayout` füllt einfach seinen Rahmen (`h-full`, kein negativer Rand).
  - Benutzt wird es nur von `ChatPane` mit Seitenleisten, also Werkstatt und `werkstatt/:sid`, beide im
    10-px-Rahmen.
- **Modellzeile bricht um:**
  - Im Projekt-Cockpit bricht der Modellname unter dem Titel in zwei Zeilen (Kopf 71 px).
  - Lösung: Die Zeile unter dem Titel bricht unter `sm` nicht um. Der Modellname wird mit „…“ gekürzt
    (`truncate`), der volle Name steht im `title`.

Weitere Akzeptanzkriterien:
- Werkstatt bei 393 und 1600 px: Die Dreispalten-Ansicht liegt vollständig im Rahmen, kein Knopf ist angeschnitten.
- Projekte bei 393 px: Chat-Kopf höchstens 64 px.
