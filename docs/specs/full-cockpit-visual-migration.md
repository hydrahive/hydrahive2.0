# Full Cockpit Visual Migration

## Ziel

Alle authentifizierten HydraHive-Seiten sollen sich wie eine zusammenhängende Anwendung anfühlen. Die Migration umfasst nicht nur die obere Navigation, sondern auch Seitenrahmen, Hintergrund, Panels, Formulare, Buttons, Tabs, Tabellen, Dialoge sowie Loading-, Empty- und Error-Zustände.

## Verbindlicher visueller Vertrag

- Hintergrund: `#080b11`; Seitenflächen: `#101724`/`#151c2b`; Eingaben: `#0d1420`.
- Rand: `#2a364b`; primärer Akzent: `#69d7ff`; Primärfläche: `#163248`.
- Radius für Panels und Controls: `4px`; keine alten `rounded-xl`/`rounded-2xl`-Seitenkarten.
- Typografie: `#e8eef8` für Primärtext, `#c8d2df` für Inhalt, `#8d9ab0` für Sekundärtext.
- Seiten verwenden einen einheitlichen Full-Height-Frame mit Cockpit-Topbar und genau einem vertikalen Scroll-Container.
- Aktionen verwenden `CockpitButton`; Flächen verwenden `CockpitPanel` oder gleichwertige Cockpit-Rahmen.
- Fachfunktionalität, API-Verträge, Datenflüsse und Berechtigungen bleiben unverändert.

## Vorgehen

1. Alle Core-Routen und installierten Modul-Routen inventarisieren.
2. Nicht migrierte Legacy-Routen durch einen gemeinsamen Cockpit-Seitenrahmen führen.
3. Settings-/Projekt-Unterseiten und Dialoge auf dieselben Cockpit-Oberflächen umstellen.
4. Modul-Quellen in ihrem jeweiligen Repository ändern; RoM ausschließlich im lokalen Gitea pflegen.
5. Mit einer begrenzten Kompatibilitätsschicht verbleibende alte Utility-Klassen innerhalb des Cockpit-Rahmens auf die verbindlichen Tokens abbilden. Keine globale Änderung außerhalb des Cockpit-Rahmens.
6. Jede Route in Desktop- und schmaler Ansicht prüfen; Build, Typecheck und fokussierte Tests ausführen.

## Akzeptanzkriterien

- Jede authentifizierte Route besitzt denselben visuellen Seitenrahmen und keine alte Theme-Topnav.
- Projekt-Einstellungen, Agenten-/Buddy-Einstellungen und Modul-Bodies zeigen keine violetten Legacy-Gradienten, großen Legacy-Radien oder hellen Legacy-Karten mehr.
- Dialoge, Tabellen, Formularfelder und Zustände verwenden dieselbe Oberfläche wie die Cockpit-Hauptseiten.
- `/projects`, `/settings/projects`, `/buddy`, `/buddy/settings`, `/werkstatt`, `/media`, `/vault`, `/admin`, `/help` sowie alle installierten Module laden ohne horizontalen Overflow.
- Funktionale Browser-Smokes bleiben grün.
