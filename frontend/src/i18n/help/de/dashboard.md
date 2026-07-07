# Dashboard

## Was ist das?

Das **Dashboard** ist deine Startseite für den Systemüberblick: Es zeigt in
**anpassbaren Kacheln (Widgets)** auf einen Blick, wie es deinem HydraHive geht —
Systemzustand, Kennzahlen, Token-Verbrauch, Verbindungen, laufende Sessions und
Server. Du kannst die Kacheln **umsortieren und ausblenden**, damit oben steht,
was dich am meisten interessiert.

## Die Widgets

- **System-Status** — schneller Gesundheits-Check (ist die KI erreichbar, läuft
  die Datenbank, sind Workspaces beschreibbar). Der erste Blick, wenn etwas hakt.
- **Kennzahlen** — die wichtigsten Zahlen: aktive Sessions, Tokens heute u.a.
- **Token-Verbrauch** — heutiger Verbrauch und Kosten, inkl. Cache-Nutzung.
  Nützlich, um Ausgaben im Blick zu behalten.
- **Verbindungen** — Status von **Tailscale** (sicheres Netzwerk) und
  **AgentLink** (Agent-zu-Agent-Kommunikation).
- **MiniMax-Nutzung** — Verbrauch, falls du MiniMax als Anbieter nutzt.
- **Sessions & Agenten** — deine letzten Konversationen und die vorhandenen
  Agenten, mit direktem Sprung hinein.
- **Server-Übersicht** — Zustand angebundener Server (falls konfiguriert).

Oben erscheint zusätzlich ein **Update-Banner**, wenn eine neue Version bereitsteht.

## Kernbegriffe

- **Agent** — eine KI-Persönlichkeit mit eigenem Modell, Werkzeugen und Rolle.
- **Session** — eine laufende oder vergangene Konversation zwischen dir (oder
  einem Auslöser) und einem Agenten.
- **Token** — die Abrechnungseinheit der Sprachmodelle; „Tokens heute" zeigt den
  Tagesverbrauch.
- **Widget** — eine einzelne Dashboard-Kachel.

## Dashboard anpassen

Die Kacheln lassen sich über die Steuerung an jeder Kachel (im **Widget-Rahmen**)
**verschieben** und **ausblenden**. Deine Anordnung wird **lokal im Browser**
gespeichert — sie bleibt also an diesem Gerät erhalten, ist aber pro Browser/Gerät
individuell.

## Schritt-für-Schritt

### Erster Rundgang
1. Oben den **System-Status** prüfen — alles grün? Dann läuft die Basis.
2. Bei **Sessions & Agenten** eine bestehende Konversation öffnen oder einen
   Agenten ansehen.
3. Über die **linke Navigation** in die Arbeitsbereiche springen (Buddy,
   Werkstatt, Projekte …).

### Wenn etwas nicht funktioniert
Zeigt der **System-Status** ein Problem (z.B. KI nicht erreichbar), findest du die
Details und Einstellungen unter **System** bzw. **LLM-Konfiguration**.

## Häufige Fragen

- **„Zahlen wirken veraltet"** — Das Dashboard lädt beim Öffnen; ein Seiten-Refresh
  holt den aktuellen Stand.
- **„Ein Widget interessiert mich nicht"** — Blende es aus; die anderen rücken auf.
- **„Wo sind ausführliche System-Details?"** — Auf der **System**-Seite (mehr
  Tiefe als das kompakte Dashboard).
- **„Kein Agent / keine Session sichtbar"** — Beim ersten Start gibt es nur den
  Master-Agenten; weitere legst du unter **Agenten** an.

## Tipps

- **Wichtigstes nach oben**: Sortier die Kacheln so, dass dein häufigster Blick
  (z.B. Token-Verbrauch oder System-Status) ganz oben ist.
- **Token-Verbrauch im Auge behalten**, wenn Kosten eine Rolle spielen — das
  Widget zeigt Tagesverbrauch und Cache-Ersparnis.
- **System-Status zuerst** bei jeder Störung — er sagt dir in Sekunden, wo es klemmt.
