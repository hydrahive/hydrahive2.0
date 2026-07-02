# Brainstorm-Anker: Theme-Templates mit Platzhaltern

> Lebendes Dokument. Hält Entscheidungen fest, damit wir nicht driften.
> KEIN Code bis Design steht. Jede Entscheidung wird hier eingetragen.

## Vision (Tills Bild)

Ein Webdesigner baut 5–6 Themes, jedes in eigenem Ordner (`/themes/theme1/`).
Ein Theme enthält **Seiten-Vorlagen** (buddy, werkstatt, atelier, …) als echtes
HTML/CSS, „höllisch grafisch aufgebohrt". An die Stellen, wo interaktive Teile
hin sollen, setzt der Designer **Platzhalter**:

```html
<div class="mein-design">
   <hh-menu type="horizontal"/>
   <hh-chatbox agent="buddy"/>
</div>
```

Die App füllt die Platzhalter mit den echten interaktiven React-Bausteinen.
Das, was heute fest in den Core-Menüs steckt, liegt dann im Theme.

## Vokabular (verbindlich)

- **Theme** — Ordner mit Seiten-Vorlagen + Style. Das Drumherum.
- **Baustein** — interaktives Element mit echter Funktion (Chatbox, Video-Editor,
  Musicplayer, Dashboard-Widget). Bringt eigenen Zustand/Daten mit.
- **Slot / Platzhalter** — `<hh-xxx/>`-Tag im Theme, wird durch einen Baustein ersetzt.
- **Template** — eine Seiten-Vorlage (HTML + Platzhalter) für eine Route.

## Grundsatz-Entscheidung: MITTELWEG (freigegeben)

Der Designer schreibt **freies HTML/CSS** für das Aussehen (volle optische
Freiheit — Layout, Farben, Verläufe, Grafiken). Die **interaktiven Teile sind
Platzhalter-Tags** (`<hh-chatbox/>`), die die App kontrolliert einsetzt.
Fremd-HTML wird **sanitized** (Scripts/gefährliches raus). **Kein eigenes JS im
Theme** — wer eigene Logik will, baut ein Modul.

= WordPress-Shortcode-Modell: freies Markup, eingezäunter interaktiver Teil.

**Bewusst akzeptierter Trade-off:** Designer kann kein eigenes JavaScript
ausführen, nur vorhandene Bausteine nutzen. Für „Seite grafisch aufbohren" reicht das.

## SICHERHEITSREGEL NR. 1 (Till, hart)

**Das aktuelle Design darf NIE verloren gehen.** Es bleibt als eingebauter
Standard + Fallback in der App. Das Template-System ist **rein additiv**:

- Ein Theme KANN eine Seite per Template überschreiben.
- Überschreibt es nicht (oder Template fehlt/bricht) → App zeigt automatisch
  die aktuelle React-Seite. Das aktuelle Design ist das Sicherheitsnetz.
- Kein Big-Bang, keine Massen-Übersetzung der 118 Seiten. Seite für Seite,
  optional, jederzeit umkehrbar.
- Layout-Sinn bereits erfüllt: „Standard"-Theme (topnav) = pixelgleich zum
  aktuellen Design, ist DEFAULT_THEME_ID, liegt auf main.

## Wichtige technische Wahrheit

- HydraHive ist eine **React-App** (Browser baut UI aus Komponenten), nicht PHP.
- Ein „Baustein" ist oft **kein simples Bild**: die Chatbox = 268 Zeilen, 11
  State-Hooks, redet mit dem Server. Solche Teile müssen einmalig
  **„droppbar" (self-contained)** gemacht werden, bevor sie an einen beliebigen
  Platzhalter passen.
- **Gute Nachricht:** Die Dashboard-Karten (TokenAudit, Tailscale, AgentLink,
  MiniMax) sind bereits self-contained ✓. Der Slot-Mechanismus existiert schon
  an 4 Stellen (moduleNav, moduleRoutes, moduleWorkspaceTabs, moduleBuddyWidgets).
- **Doppelnutzen:** Die gekapselten Bausteine sind gleichzeitig die
  UI-Bausteinbibliothek (die „Alternative zu Nuxt UI" / das UI-Kit). Ein Baustein
  ist droppbar UND wiederverwendbares UI-Element.

## Ausbaustufen (Zielbild, grob → fein)

1. Bausteine als Platzhalter einsetzbar (`<hh-chatbox/>`).
2. Eigene Seiten aus Platzhaltern zusammenstellbar.
3. Theme liefert Seiten-Templates mit (nicht nur Layout).
4. Core-Menüpunkte werden zu Theme-Vorlagen (überschreibbar).
5. Parameter am Platzhalter (`<hh-chatbox agent="buddy"/>`).
6. Marktplatz-Reife (Themes + Bausteine über Hub teilen).

## Offene Entscheidungen (zu klären, bevor Code)

- [ ] **Baustein-Katalog v1:** Welche Bausteine braucht die erste Runde? Kandidaten:
      `hh-menu` (horizontal/vertikal), `hh-chatbox` (buddy/werkstatt),
      `hh-dashboard-widget`, `hh-musicplayer`, `hh-videoeditor`?
- [ ] **Platzhalter-Syntax:** `<hh-chatbox agent="buddy"/>` (HTML-Custom-Tag) vs.
      `[[chatbox:buddy]]` (Shortcode-Text)? → beeinflusst Parser.
- [ ] **Template-Format:** reine `.html`-Dateien pro Route? Oder `.html` + `theme.json`
      (Style) getrennt?
- [ ] **Welche Seiten zuerst** als Template verfügbar? (buddy zuerst = Proof)
- [ ] **Sanitizing-Regeln:** welche HTML-Tags/Attribute erlaubt, was fliegt raus?
- [ ] **Theme ↔ Modul-Konflikt:** wenn beide eine Seite liefern — wer gewinnt?
- [ ] **Rollen:** wer darf Templates bearbeiten/installieren? (Designer/Admin/User)
- [ ] **Daten-Versorgung:** jeder Baustein holt seine Daten selbst (Regel).

## Proof-first Plan (gegen Drift)

Bevor das ganze Register gebaut wird: **EIN** Theme-Ordner, **eine** `buddy.html`
mit **einem** Platzhalter `<hh-chatbox/>`. Sichtbar machen: Designer-HTML drumherum
+ echte Chatbox drin. Erst wenn das steht und sich richtig anfühlt → hochziehen.

## Nicht in diesem Feature

- Designer-eigenes JavaScript im Theme (= Modul-Territorium).
- Visueller Drag&Drop-Theme-Editor (evtl. viel später).
- Server-seitiges Rendering (bleibt Client-React).

## Ideen-Halde (Tills „wirre Dinge" — unsortiert, willkommen)

- **WYSIWYG-Template-Editor (Till, 2026-07-02):** ein visueller Editor für die
  Theme-Templates — Vorbild: unser Blueprint/Butler-Node-Editor (@xyflow/react
  ist schon im Projekt!). Statt HTML zu tippen, Bausteine per Klick/Drag auf eine
  Leinwand ziehen, Attribute in einem Panel setzen. Ausgabe = dasselbe Template-
  HTML wie heute (Editor UND Handschrift bleiben kompatibel, weil beide dasselbe
  <hh-…/>-Format erzeugen). Erst NACH dem „kompletten Satz" (Seiten + Bausteine)
  bauen — der Editor ist die Kür, die Bausteine sind die Pflicht.
